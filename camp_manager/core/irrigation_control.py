import json

async def force_irrigation(mqtt_client, current_moisture: float = 0.0, irrigation_amount: float = 25.0):
    print(f"Publishing command to FORCE irrigate. (Current moisture: {current_moisture}%)", flush=True)
    payload = str(irrigation_amount)
    await mqtt_client.publish("terrain/cmd/irrigate", payload)


async def auto_irrigate(mqtt_client, current_moisture: float, min_moisture: float = 20.0, irrigation_amount: float = 13.0):
    minimal_moisture = max(min_moisture, 20.0)
    if current_moisture <= minimal_moisture:
        print(f"Moisture level ({current_moisture}%) fell below safety minimum ({minimal_moisture}%). Auto-irrigating!", flush=True)
        await force_irrigation(mqtt_client, current_moisture, irrigation_amount)