import asyncio
import ssl
import aiomqtt

from core.communication_par_amb import (
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
)
from core.manager import SensorManager
from interfaces.mqtt_client import publish_data

KNOWN_CAMPS = ["campo_1", "campo_2", "campo_3"]


async def publish_loop(client, managers):
    while True:
        for camp_id, manager in managers.items():
            state = manager.get_state()
            topic = f"camp/{camp_id}/environment/telemetry"
            await publish_data(client, topic, state)
            manager.update_environment()

        await asyncio.sleep(10)


async def listen_mqtt_commands(client, managers):
    await client.subscribe("camp/+/environment/cmd/#")

    async for msg in client.messages:
        top = str(msg.topic)
        raw = msg.payload.decode("utf-8") if isinstance(msg.payload, bytes) else str(msg.payload)

        parts = top.split("/")
        if len(parts) >= 2 and parts[0] == "camp":
            camp_id = parts[1]
        else:
            continue

        if camp_id not in managers:
            managers[camp_id] = SensorManager(d=1, m=1, y=2026)

        manager = managers[camp_id]

        if top.endswith("/skip"):
            try:
                days = int(raw.strip())
            except ValueError:
                days = 1

            st = manager.get_state()
            for _ in range(days):
                manager.update_environment()
                st = manager.get_state()
                topic = f"camp/{camp_id}/environment/telemetry"
                await publish_data(client, topic, st)
                await asyncio.sleep(0.1)

            print(
                f"[AMBIENT SENSOR] [{camp_id.upper()}] Skipped {days} days. Current date: {st['day']:02d}/{st['month']:02d}/{st['year']}",
                flush=True,
            )

        elif top.endswith("/reset"):
            manager._create_timer_state(d=1, m=1, y=2026)
            print(f"[AMBIENT SENSOR] [{camp_id.upper()}] Environment state reset to 01/01/2026.", flush=True)
            topic = f"camp/{camp_id}/environment/telemetry"
            await publish_data(client, topic, manager.get_state())


async def worker(managers):
    ssl_ctx = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_ctx,
        identifier="ambient-sensor-app",
    )
    async with client:
        print("[AMBIENT SENSOR] Multi-camp service online. Starting tasks...", flush=True)

        t1 = asyncio.create_task(publish_loop(client, managers))
        t2 = asyncio.create_task(listen_mqtt_commands(client, managers))

        done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                raise task.exception()


async def main():
    managers = {cid: SensorManager(d=1, m=1, y=2026) for cid in KNOWN_CAMPS}
    print("[AMBIENT SENSOR] Starting multi-camp ambient node...", flush=True)

    while True:
        try:
            await worker(managers)
        except Exception as err:
            print(f"[AMBIENT SENSOR] Connection dropped ({err}). Reconnecting in 5s...", flush=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())