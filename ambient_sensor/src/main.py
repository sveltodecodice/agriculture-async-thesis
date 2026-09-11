import asyncio
import ssl
import aiomqtt

from core.communication_par_amb import (
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    TELEMETRY_ENV_TOPIC,
)
from core.manager import SensorManager
from interfaces.mqtt_client import publish_data


async def publish_loop(client, manager):
    while True:
        state = manager.get_state()
        await publish_data(client, TELEMETRY_ENV_TOPIC, state)
        
        d, m, y = state["day"], state["month"], state["year"]
        print(
            f"[AMBIENT SENSOR] --- {d:02d}/{m:02d}/{y} | {state['season']} | "
            f"Temp: {state['temperature']}°C | Weather: {state['weather']} | "
            f"Wind: {state['wind_kmh']} km/h | Rad: {state['radiation_wm2']} W/m² | Rain: {state['rain_mm']} mm ---",
            flush=True,
        )
        await asyncio.sleep(10)
        manager.update_environment()


async def listen_mqtt_commands(client, manager):
    await client.subscribe("environment/cmd/#")
    async for msg in client.messages:
        top = str(msg.topic)
        raw = msg.payload.decode("utf-8") if isinstance(msg.payload, bytes) else str(msg.payload)

        if top.endswith("/skip"):
            try:
                days = int(raw.strip())
            except ValueError:
                days = 1
                
            for _ in range(days):
                manager.update_environment()
                st = manager.get_state()
                # SPOSTATO DENTRO IL CICLO: pubblica ogni singolo giorno saltato
                await publish_data(client, TELEMETRY_ENV_TOPIC, st)
                # Piccola pausa per permettere a terrain_sensor e dashboard di elaborare il giorno
                await asyncio.sleep(0.2) 
                
            print(
                f"[AMBIENT SENSOR] Skipped {days} days. Current date: {st['day']:02d}/{st['month']:02d}/{st['year']}",
                flush=True,
            )

        elif top.endswith("/reset"):
            manager._create_timer_state(d=1, m=1, y=2026)
            print("[AMBIENT SENSOR] Environment state reset to 01/01/2026.", flush=True)
            await publish_data(client, TELEMETRY_ENV_TOPIC, manager.get_state())
            
async def worker(manager):
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
        print("[AMBIENT SENSOR] Service online. Starting tasks...", flush=True)

        t1 = asyncio.create_task(publish_loop(client, manager))
        t2 = asyncio.create_task(listen_mqtt_commands(client, manager))

        done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                raise task.exception()


async def main():
    manager = SensorManager(d=1, m=1, y=2026)
    print("[AMBIENT SENSOR] Starting ambient telemetry node...", flush=True)

    while True:
        try:
            await worker(manager)
        except Exception as err:
            print(f"[AMBIENT SENSOR] Connection dropped ({err}). Reconnecting in 5s...", flush=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())