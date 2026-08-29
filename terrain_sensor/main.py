import asyncio
import json
import os
import aiomqtt

from core.condizione_terreno import create_terrain_state, update_terrain

broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
broker_port = int(os.getenv('MQTT_BROKER_PORT', 1883))

state = create_terrain_state(initial_moisture=50.0)


async def process_ambient_data(client, payload_str):
    data = json.loads(payload_str)

    # Calculate new soil moisture and oxygenation
    update_terrain(state, data["weather"], data["temperature"])

    # Payload prepared for camp_manager
    terrain_telemetry = {
        "date": f"{data['day']:02d}/{data['month']:02d}/{data['year']}",
        "season": data["season"],
        "temperature": data["temperature"],
        "weather": data["weather"],
        "soil_moisture": state["soil_moisture"],
        "oxygenation": state["oxygenation"],
        "irrigation_active": state["irrigation_active"]
    }

    # Publish telemetry to camp_manager
    await client.publish("camp/terrain_telemetry", json.dumps(terrain_telemetry), qos=1)
    print(
        f"[{terrain_telemetry['date']}] Moisture: {state['soil_moisture']}% | "
        f"O2: {state['oxygenation']}% | Pump: {state['irrigation_active']}",
        flush=True
    )


async def main():
    while True:
        try:
            async with aiomqtt.Client(hostname=broker_host, port=broker_port) as client:
                await client.subscribe("environment/telemetry")
                print("Terrain sensor active. Routing calculations to camp_manager...", flush=True)

                async for msg in client.messages:
                    if str(msg.topic) == "environment/telemetry":
                        await process_ambient_data(client, msg.payload.decode())

        except Exception as err:
            print(f"Terrain sensor connection error ({err}). Retrying in 5s...", flush=True)
            await asyncio.sleep(5)


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Terrain sensor stopped manually", flush=True)