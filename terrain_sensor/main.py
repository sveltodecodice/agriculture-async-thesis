import asyncio 
import json 
import os
import aiomqtt

from core.terrain_condition import create_terrain_state, process_terrain_update

MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
broker_user = os.getenv("MQTT_BROKER_USER", "farm_admin")
broker_pass = os.getenv("MQTT_BROKER_PASS", "secure_farm")

initial_state = create_terrain_state(initial_moisture=50.0, initial_oxygen=70.0)

async def consume_stream(client):
    async for msg in client.messages:
        topic = str(msg.topic)
        payload_str = msg.payload.decode()

        if topic == "environment/telemetry":
            ambient_data = json.loads(payload_str)
            telemetry = process_terrain_update(initial_state, ambient_data)
            initial_state["irrigation_active"] = False

            await client.publish("camp/terrain_telemetry", json.dumps(telemetry), qos=1)
            print(
                f"[{telemetry['date']}] Moisture: {telemetry['soil_moisture']:.1f}% | "
                f"O2: {telemetry['oxygenation']:.1f}% | Pump: {telemetry['irrigation_active']}",
                flush=True
            )

        elif topic == "terrain/cmd/irrigate":
            initial_state["irrigation_active"] = True
            print("[TERRAIN] Irrigation requested! Pump activated for the next tick.", flush=True)

        elif topic == "terrain/cmd/reoxygenate":
            initial_state["oxygenation"] = 100.0
            print("[TERRAIN] Soil successfully reoxygenated to 100.0%!", flush=True)

        elif topic in ["terrain/cmd/reset", "environment/cmd/reset", "camp_manager/cmd/reset"]:
            fresh_state = create_terrain_state(initial_moisture=50.0)
            initial_state.clear()
            initial_state.update(fresh_state)
            print("[TERRAIN] Sensor reset back to Day 1 initial state.", flush=True)

async def connect_and_listen():
    async with aiomqtt.Client(
        hostname=MQTT_BROKER,
        port=MQTT_PORT,
        username=broker_user,
        password=broker_pass
    ) as client:
        await client.subscribe("environment/telemetry")
        await client.subscribe("terrain/cmd/irrigate")
        await client.subscribe("terrain/cmd/reoxygenate")
        await client.subscribe("terrain/cmd/reset")
        await client.subscribe("environment/cmd/reset")
        await client.subscribe("camp_manager/cmd/reset")
        
        print("Terrain sensor active, listening...", flush=True)
        await consume_stream(client)


async def main():
    while True:
        try:
            await connect_and_listen()
        except aiomqtt.MqttError:
            print("MQTT connection dropped. Reconnecting in 5s...", flush=True)
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Operational error: {e}", flush=True)
            await asyncio.sleep(2)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass