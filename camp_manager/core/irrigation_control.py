# irrigation_control.py
async def force_irrigation(mqtt_client, current_moisture: float, irrigation_amount: float = 25.0):
    print(f"Publishing command to FORCE irrigate. (Current moisture: {current_moisture}%)", flush=True)
    await mqtt_client.publish(
        topic="terrain/cmd/irrigate",
        payload=str(irrigation_amount)
    )

async def auto_irrigate(mqtt_client, current_moisture: float, min_moisture: float = 20.0, irrigation_amount: float = 25.0):
    # Enforce minimum minimal_moisture floor of 20.0%
    minimal_moisture = max(min_moisture, 20.0)
    
    if current_moisture <= minimal_moisture:
        print(f"Moisture level ({current_moisture}%) fell below safety minimum ({minimal_moisture}%). Auto-irrigating!", flush=True)
        await force_irrigation(mqtt_client, current_moisture, irrigation_amount)