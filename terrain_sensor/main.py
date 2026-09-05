import asyncio 
import json 
import os
import aiomqtt

from core.terrain_condition import create_terrain_state, process_terrain_update

MQTT_BROKER = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

initial_state = create_terrain_state(initial_moisture=50.0)

async def consume_stream(client):
    """Nesting livello 1: aspetta i messaggi in ingresso"""
    async for msg in client.messages:
        topic = str(msg.topic)
        payload_str = msg.payload.decode()

        # 1. Handle normal environment updates
        if topic == "environment/telemetry":
            ambient_data = json.loads(payload_str)
            
            # Process the telemetry math first while irrigation_active is STILL True
            telemetry = process_terrain_update(initial_state, ambient_data)
            
            # Reset the pump state AFTER the update calculations complete
            initial_state["irrigation_active"] = False

            await client.publish("camp/terrain_telemetry", json.dumps(telemetry), qos=1)
            print(
                f"[{telemetry['date']}] Moisture: {telemetry['soil_moisture']:.1f}% | "
                f"O2: {telemetry['oxygenation']:.1f}% | Pump: {telemetry['irrigation_active']}",
                flush=True
            )

        # 2. Handle forced irrigation commands from the Camp Manager
        elif topic == "terrain/cmd/irrigate":
            initial_state["irrigation_active"] = True
            print("[TERRAIN] Irrigation requested! Pump activated for the next tick.", flush=True)

        # 3. Handle reoxygenation commands from the Camp Manager
        elif topic == "terrain/cmd/reoxygenate":
            initial_state["oxygenation"] = 100.0
            print("[TERRAIN] Soil successfully reoxygenated to 100.0%!", flush=True)


async def connect_and_listen():
    """Nesting livello 1: gestisce la sessione del client"""
    async with aiomqtt.Client(hostname=MQTT_BROKER, port=MQTT_PORT) as client:
        # Subscribe to all required topics
        await client.subscribe("environment/telemetry")
        await client.subscribe("terrain/cmd/irrigate")
        await client.subscribe("terrain/cmd/reoxygenate")
        
        print("Terrain sensor active, listening...", flush=True)
        await consume_stream(client)


async def main():
    """Nesting livello 2: loop di retry in caso di disconnessione"""
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