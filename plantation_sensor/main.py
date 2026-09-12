import asyncio
import json
import ssl
import aiomqtt

from core.communication_par_pla import (
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
)
from core.mqtt_utils import Deduper, publish_json
from core.plant_conditions import (
    advance_days,
    clear_field,
    create_default_plantation_state,
    get_status,
    reset,
    seed_planted,
)

KNOWN_CAMPS = ["campo_1", "campo_2", "campo_3"]


def create_camp_context():
    return {
        "moisture": None,
        "last_date": None,
        "plantation": create_default_plantation_state(),
    }


async def monitor_loop(mqtt, camp_contexts):
    while True:
        await asyncio.sleep(3)
        for camp_id, ctx in camp_contexts.items():
            status = get_status(ctx["plantation"], ctx["moisture"])
            status_topic = f"camp/{camp_id}/plantation/status"
            await publish_json(mqtt, status_topic, status)

            detail = status["status_detail"]
            await mqtt.publish(f"camp/{camp_id}/plantation/plant_name", str(detail["plant_name"]))
            await mqtt.publish(f"camp/{camp_id}/plantation/time_left", str(detail["time_left"]))
            await mqtt.publish(f"camp/{camp_id}/plantation/health", str(detail["health"]))


async def listen_mqtt_telemetry(mqtt, camp_contexts, dedup):
    await mqtt.subscribe("camp/+/terrain/telemetry")
    await mqtt.subscribe("camp/+/environment/telemetry")
    await mqtt.subscribe("camp/+/plantation/cmd/#")

    async for msg in mqtt.messages:
        top = str(msg.topic)
        raw = msg.payload.decode("utf-8") if isinstance(msg.payload, bytes) else str(msg.payload)

        parts = top.split("/")
        if len(parts) >= 2 and parts[0] == "camp":
            camp_id = parts[1]
        else:
            continue

        if camp_id not in camp_contexts:
            camp_contexts[camp_id] = create_camp_context()

        ctx = camp_contexts[camp_id]

        if "terrain/telemetry" in top:
            pkt = json.loads(raw)
            if dedup.is_duplicate_or_stale(top, pkt.get("ts")):
                continue
            if "soil_moisture" in pkt:
                ctx["moisture"] = float(pkt["soil_moisture"])

        elif "environment/telemetry" in top:
            pkt = json.loads(raw)
            if dedup.is_duplicate_or_stale(top, pkt.get("ts")):
                continue

            new_date = pkt.get("date")
            if new_date and new_date != ctx.get("last_date"):
                ctx["last_date"] = new_date
                advance_days(ctx["plantation"], 1)

        elif "plantation/cmd/" in top:
            cmd = top.split("plantation/cmd/")[-1].lower()
            if cmd == "plant":
                try:
                    seed_data = json.loads(raw)
                except Exception:
                    seed_data = {"name": raw.strip()}
                seed_planted(ctx["plantation"], seed_data)
                print(f"[PLANTATION SENSOR] [{camp_id.upper()}] Planted seed: {seed_data.get('name')}", flush=True)
            elif cmd == "clear":
                clear_field(ctx["plantation"])
                print(f"[PLANTATION SENSOR] [{camp_id.upper()}] Field cleared.", flush=True)
            elif cmd in ("reset", "restart"):
                reset(ctx["plantation"])
                print(f"[PLANTATION SENSOR] [{camp_id.upper()}] State reset.", flush=True)


async def worker(camp_contexts, dedup):
    ssl_ctx = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_ctx,
        identifier="plantation-sensor-app",
    )
    async with client:
        print("[PLANTATION SENSOR] Multi-camp subsystem online.", flush=True)
        t1 = asyncio.create_task(monitor_loop(client, camp_contexts))
        t2 = asyncio.create_task(listen_mqtt_telemetry(client, camp_contexts, dedup))

        done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                raise task.exception()


async def main():
    camp_contexts = {cid: create_camp_context() for cid in KNOWN_CAMPS}
    dedup = Deduper()

    while True:
        try:
            await worker(camp_contexts, dedup)
        except Exception as err:
            print(f"[PLANTATION SENSOR] Connection dropped ({err}). Reconnecting in 5s...", flush=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())