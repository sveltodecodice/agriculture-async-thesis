import asyncio
import os
import aiomqtt

from core.manager import create_timer_state, update_environment
from core.mqtt_client import publish_data, listen_commands

broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
broker_port = int(os.getenv('MQTT_BROKER_PORT', 1883))
broker_user = os.getenv("MQTT_BROKER_USER", "farm_admin")
broker_pass = os.getenv("MQTT_BROKER_PASS", "secure_farm")
telemetry_topic = "environment/telemetry"


def create_skip_handler(state, client, topic):
    async def handle_skip_day(payload):
        try:
            days_to_skip = int(payload)
            for _ in range(days_to_skip):
                update_environment(state)
                await publish_data(client, topic, state)
            print(
                f"[SKIP] Skipped {days_to_skip} days. New date: {state['day']:02d}/{state['month']:02d}/{state['year']}",
                flush=True
            )
        except ValueError:
            print(f"[ERROR] Payload skip not valid: {payload}", flush=True)
    return handle_skip_day


def create_reset_handler(state, client, topic):
    async def handle_reset(payload):
        try:
            # Reset the timer state back to Day 1
            new_state = create_timer_state(d=1, m=1, y=2026)
            state.update(new_state)
            await publish_data(client, topic, state)
            print("[ENVIRONMENT] Sensor reset to initial date: 01/01/2026", flush=True)
        except Exception as e:
            print(f"[ERROR] Environment reset failed: {e}", flush=True)
    return handle_reset


async def run_telemetry_loop(client, state):
    while True:
        # Publish and log current day immediately before sleeping/updating
        await publish_data(client, telemetry_topic, state)
        log_msg = (
            f"[{state['day']:02d}/{state['month']:02d}/{state['year']}] "
            f"Season: {state['season']:<8} | Temp: {state['temperature']:>2}°C | "
            f"Weather: {state['weather']:<8}"
        )
        print(log_msg, flush=True)

        await asyncio.sleep(10)
        
        update_environment(state)


async def session_runner(state):
    async with aiomqtt.Client(
        hostname=broker_host,
        port=broker_port,
        username=broker_user,
        password=broker_pass
    ) as client:
        handlers = {
            "environment/skip_day": create_skip_handler(state, client, telemetry_topic),
            "environment/cmd/reset": create_reset_handler(state, client, telemetry_topic)
        }
        
        asyncio.create_task(listen_commands(client, handlers))
        await run_telemetry_loop(client, state)


async def main():
    
    start_state = create_timer_state(d=1, m=1, y=2026)

    while True:
        try:
            await session_runner(start_state)
        except Exception as e:
            print(f"Connection error({e}). Trying in 5 second...", flush=True)
            await asyncio.sleep(5)
            
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("script stopped manually", flush=True)