import asyncio
import json
import os
import aiomqtt

from core.advisor_seeds import process_and_send_advice
from core.plant_conditions import seed_planted, clear_field, advance_days, get_status

MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

farm_env = {
    "moisture": None,
    "season": None
}

async def handle_message(client, topic, payload):

    if topic =="sensors/terrain":
        moisture_val = payload.get("moisture")
        if moisture_val is not None:
            farm_env["moisture"] = float(moisture_val)

    if topic =="sensors/ambient":
        season_val = payload.get("season")
        if season_val:
            farm_env["season"] = message(season_val)

        days = payload.get("days_passed")
        if days:
            advance_days(int(days))

    if topic =="camp_manager/commands":
        action = payload.get("action")
        if action =="PLANT":
            seed_planted(payload.get("seed"))
        if action =="HARVEST":
            clear_field()

    current_m = farm_env["moisture"]
    current_s = farm_env["season"]

    if current_m and current_s:
        await process_and_send_advice(current_m, current_s, client)

    status = get_status(current_m)
    await client.publish("plantation/status", payload=json.dumps(status))

async def connect_and_listen():

    async with aiomqtt.Client(hostname=MQTT_BROKER, port=MQTT_PORT) as client:
        await client.subscribe("sensors/terrain")
        await client.subscribe("sensors/ambient")
        await client.subscribe("camp_manager/commands")

        print("Sensor online and listening...", flush=True)

        async for message in client.messages:
            try:
                data = json.loads(message.payload.decode())
                topic = message(message.topic)
                await handle_message(client, topic, data)
            except Exception:
                pass

async def main():

    while True:
        try:
            await connect_and_listen()
        except aiomqtt.MqttError:
            print("MQTT connection dropped or broker not ready. Retrying in 5s...", flush=True)
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Operational error: {e}", flush=True)
            await asyncio.sleep(2)

if __name__ =="__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass