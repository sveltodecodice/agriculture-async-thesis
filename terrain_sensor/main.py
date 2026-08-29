import asyncio, json, os
import aiomqtt
from core.terrain_condition import create_terrain_state, process_terrain_update

HOST = os.getenv('MQTT_BROKER_HOST', 'localhost')
PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))

st = create_terrain_state(initial_moisture=50.0)


async def consume_stream(client):
    """Nesting livello 1: aspetta i messaggi in ingresso"""
    async for msg in client.messages:
        ambient_data = json.loads(msg.payload.decode())
        telemetry = process_terrain_update(st, ambient_data)

        await client.publish("camp/terrain_telemetry", json.dumps(telemetry), qos=1)
        print(
            f"[{telemetry['date']}] Moisture: {telemetry['soil_moisture']}% | "
            f"O2: {telemetry['oxygenation']}% | Pump: {telemetry['irrigation_active']}",
            flush=True
        )


async def connect_and_listen():
    """Nesting livello 1: gestisce la sessione del client"""
    async with aiomqtt.Client(hostname=HOST, port=PORT) as client:
        await client.subscribe("environment/telemetry")
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