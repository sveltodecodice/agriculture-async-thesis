import asyncio
import os
import aiomqtt

from core.manager import create_timer_state, update_environment
from core.mqtt_client import publish_data, listen_commands

broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
broker_port = int(os.getenv('MQTT_BROKER_PORT', 1883))
telemetry_topic = "environment/telemetry"


def create_skip_handler(state):
    def handle_skip_day(payload):
        try:
            days_to_skip = int(payload)
            for _ in range(days_to_skip):
                update_environment(state)
            print(
                f"[SKIP] Avanzati {days_to_skip} giorni. Nuova data: {state['day']:02d}/{state['month']:02d}/{state['year']}", 
                flush=True
            )
        except ValueError:
            print(f"[ERRORE] Payload skip non valido: {payload}", flush=True)
    return handle_skip_day


async def run_telemetry_loop(client, state):
    while True:
        # Publish and log current day immediately before sleeping/updating
        await publish_data(client, telemetry_topic, state)
        log_msg = (
            f"[{state['day']:02d}/{state['month']:02d}/{state['year']}] "
            f"Season: {state['season']:<8} | Temp: {state['temperature']:>2}°C | "
            f"Weather: {state['weather']:<8} | Soil moisture: {state['soil_moisture']}%"
        )
        print(log_msg, flush=True)
        
        await asyncio.sleep(10)
        update_environment(state)


async def session_runner(state, handlers):
    async with aiomqtt.Client(hostname=broker_host, port=broker_port) as client:
        asyncio.create_task(listen_commands(client, handlers))
        await run_telemetry_loop(client, state)


async def main():
    curr_state = create_timer_state(d=1, m=1, y=2026, initial_moisture=50.0)
    handlers = {"environment/skip_day": create_skip_handler(curr_state)}

    while True:
        try:
            await session_runner(curr_state, handlers)
        except Exception as e:
            print(f"Errore di connessione ({e}). Riprovo tra 5 secondi...", flush=True)
            await asyncio.sleep(5)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("script stopped manually", flush=True)