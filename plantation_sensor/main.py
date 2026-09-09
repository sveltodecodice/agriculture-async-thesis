import asyncio
import json
import ssl
import aiomqtt

from core.amqp_listener import consume_amqp_commands
from core.communication_par_pla import (
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    PLANTATION_STATUS_TOPIC,
    TELEMETRY_ENV_TOPIC,
    TELEMETRY_TERRAIN_TOPIC,
)
from core.mqtt_utils import Deduper, publish_json
from core.plant_conditions import advance_days, get_status


async def monitor_loop(mqtt, state):
    while True:
        await asyncio.sleep(5)
        status = get_status(state["moisture"])
        await publish_json(mqtt, PLANTATION_STATUS_TOPIC, status)


async def listen_mqtt_telemetry(mqtt, state, dedup):
    await mqtt.subscribe(TELEMETRY_TERRAIN_TOPIC)
    await mqtt.subscribe(TELEMETRY_ENV_TOPIC)

    async for msg in mqtt.messages:
        top = str(msg.topic)
        raw = msg.payload.decode()

        if top == TELEMETRY_TERRAIN_TOPIC:
            pkt = json.loads(raw)
            if dedup.is_duplicate_or_stale(TELEMETRY_TERRAIN_TOPIC, pkt.get("ts")):
                continue
            if "soil_moisture" in pkt:
                state["moisture"] = float(pkt["soil_moisture"])

        elif top == TELEMETRY_ENV_TOPIC:
            pkt = json.loads(raw)
            if dedup.is_duplicate_or_stale(TELEMETRY_ENV_TOPIC, pkt.get("ts")):
                continue
            
            new_date = pkt.get("date")
            if new_date and new_date != state.get("last_date"):
                state["last_date"] = new_date
                advance_days(1)


async def worker(state, dedup):
    ssl_ctx = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_ctx
    )
    async with client:
        print("Plantation subsystem online.")
        t1 = asyncio.create_task(monitor_loop(client, state))
        t2 = asyncio.create_task(listen_mqtt_telemetry(client, state, dedup))
        t3 = asyncio.create_task(consume_amqp_commands(state, dedup, client))

        done, pending = await asyncio.wait([t1, t2, t3], return_when=asyncio.FIRST_EXCEPTION)

        # Annulla subito le altre task pendenti per sbloccare la riconnessione
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                raise task.exception()


async def main():
    state = {"moisture": None, "last_date": None}
    dedup = Deduper()

    while True:
        try:
            await worker(state, dedup)
        except Exception as err:
            print(f"Plantation node connection dropped ({err}). Reconnecting in 5s...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())