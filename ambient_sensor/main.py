import asyncio
import aiomqtt

from core.amqp_listener import consume_amqp_commands
from core.communication_par_amb import MQTT_HOST, MQTT_PASS, MQTT_PORT, MQTT_USER, TELEMETRY_TOPIC
from core.manager import create_timer_state, update_environment
from core.mqtt_client import publish_data


async def publish_loop(client, state):
    while True:
        await publish_data(client, TELEMETRY_TOPIC, state)
        d, m, y = state["day"], state["month"], state["year"]
        print(f"--- {d:02d}/{m:02d}/{y} | {state['season']} | {state['temperature']}°C | {state['weather']} ---")
        update_environment(state)
        await asyncio.sleep(10)


async def worker(state):
    client = aiomqtt.Client(MQTT_HOST, MQTT_PORT, username=MQTT_USER, password=MQTT_PASS)
    async with client:
        print("Ambient sensor online. Launching tasks...")
        t1 = asyncio.create_task(publish_loop(client, state))
        t2 = asyncio.create_task(consume_amqp_commands(state, client))

        done, _ = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            if task.exception():
                raise task.exception()


async def main():
    state = create_timer_state(d=1, m=1, y=2026)
    print("Starting ambient telemetry node...")

    while True:
        try:
            await worker(state)
        except Exception as err:
            print(f"Ambient node connection dropped ({err}). Reconnecting in 5s...")
            await asyncio.sleep(5)


asyncio.run(main())