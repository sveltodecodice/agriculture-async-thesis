import asyncio
import json
import ssl
import aiomqtt

from core.amqp_listener import consume_amqp_commands
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
    async for msg in client.messages:
        if str(msg.topic) == TELEMETRY_IN_TOPIC:
            ambient_data = json.loads(msg.payload.decode())
            if dedup.is_duplicate_or_stale(TELEMETRY_IN_TOPIC, ambient_data.get("ts")):
                continue

            telemetry = process_terrain_update(state, ambient_data)
            state["irrigation_active"] = False

            await publish_json(client, TELEMETRY_OUT_TOPIC, telemetry, qos=1)
            print(
                f"[{telemetry['date']}] Moisture: {telemetry['soil_moisture']:.1f}% | "
                f"O2: {telemetry['oxygenation']:.1f}% | Pump: {telemetry['irrigation_active']}"
            )


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
    )
    async with client:
        print("Service online. Starting tasks...")

        t1 = asyncio.create_task(listen_mqtt_telemetry(client, state, dedup))
        t2 = asyncio.create_task(consume_amqp_commands(state, client))

        done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                raise task.exception()


async def main():
    state = create_terrain_state(initial_moisture=50.0, initial_oxygen=70.0)
    dedup = Deduper()

    while True:
        try:
            await worker(state, dedup)
        except Exception as err:
            print(f"Terrain node connection dropped ({err}). Reconnecting in 5s...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())