import asyncio
import json
import ssl
import aiomqtt

from core.communication_par_ter import (
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    TELEMETRY_IN_TOPIC,
    TELEMETRY_OUT_TOPIC,
)
from core.mqtt_utils import Deduper, publish_json
from core.terrain_condition import create_terrain_state, process_terrain_update


async def listen_mqtt_telemetry(client, state, dedup):
    await client.subscribe(TELEMETRY_IN_TOPIC)
    await client.subscribe("terrain/cmd/#")

    async for msg in client.messages:
        top = str(msg.topic)
        raw = msg.payload.decode("utf-8") if isinstance(msg.payload, bytes) else str(msg.payload)

        if top == TELEMETRY_IN_TOPIC:
            ambient_data = json.loads(raw)
            if dedup.is_duplicate_or_stale(TELEMETRY_IN_TOPIC, ambient_data.get("ts")):
                continue

            telemetry = process_terrain_update(state, ambient_data)
            state["irrigation_active"] = False

            await publish_json(client, TELEMETRY_OUT_TOPIC, telemetry, qos=1)
            print(
                f"[TERRAIN SENSOR] [{telemetry['date']}] Soil: {telemetry.get('soil_type', 'Loam')} | "
                f"Moisture: {telemetry['soil_moisture']:.1f}% | O2: {telemetry['oxygenation']:.1f}% | "
                f"Pump: {telemetry['irrigation_active']}",
                flush=True,
            )

        elif top.startswith("terrain/cmd/"):
            cmd = top.replace("terrain/cmd/", "").lower()

            if cmd in ("irrigate", "force_irrigate", "force_irrigation"):
                amount = 15.0
                try:
                    if raw and not raw.startswith("{"):
                        amount = float(raw)
                except ValueError:
                    pass
                state["soil_moisture"] = min(100.0, state["soil_moisture"] + amount)
                state["irrigation_active"] = True
                print(f"[TERRAIN SENSOR] Irrigated (+{amount:.1f}%)! New moisture: {state['soil_moisture']:.1f}%.", flush=True)

            elif cmd in ("reoxygenate", "oxygen"):
                state["oxygenation"] = 100.0
                print("[TERRAIN SENSOR] Soil reoxygenated to 100.0%.", flush=True)

            elif cmd in ("set_soil_type", "set_type"):
                state["soil_type"] = raw.strip()
                print(f"[TERRAIN SENSOR] Soil type set to: {state['soil_type']}", flush=True)

            elif cmd in ("reset", "restart"):
                state["soil_moisture"] = 50.0
                state["oxygenation"] = 70.0
                state["soil_type"] = "Loam"
                state["irrigation_active"] = False
                dedup.reset()
                print("[TERRAIN SENSOR] Terrain sensor state reset.", flush=True)

            telemetry = {
                "soil_moisture": state["soil_moisture"],
                "oxygenation": state["oxygenation"],
                "soil_type": state.get("soil_type", "Loam"),
                "irrigation_active": state["irrigation_active"],
                "date": state.get("date", "01/01/2026"),
            }
            await publish_json(client, TELEMETRY_OUT_TOPIC, telemetry, qos=1)


async def worker(state, dedup):
    ssl_ctx = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_ctx,
        identifier="terrain-sensor-app",
    )
    async with client:
        print("[TERRAIN SENSOR] Service online. Starting tasks...", flush=True)

        t1 = asyncio.create_task(listen_mqtt_telemetry(client, state, dedup))

        done, pending = await asyncio.wait([t1], return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                raise task.exception()


async def main():
    state = create_terrain_state(initial_moisture=50.0, initial_oxygen=70.0, soil_type="Loam")
    dedup = Deduper()

    while True:
        try:
            await worker(state, dedup)
        except Exception as err:
            print(f"[TERRAIN SENSOR] Connection dropped ({err}). Reconnecting in 5s...", flush=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())