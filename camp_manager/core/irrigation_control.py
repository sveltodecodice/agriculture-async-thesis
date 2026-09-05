async def force_irrigation(mqtt_client, current_moisture: float, irrigation_amount: float = 20.0):
    print(f"[CAMP MANAGER] Publishing command to FORCE irrigate. (Current moisture: {current_moisture})", flush=True)
    await mqtt_client.publish(
        topic="terrain/cmd/irrigate",
        payload=str(irrigation_amount)
    )

async def auto_irrigate(mqtt_client, current_moisture: float, min_moisture: float = 20.0, irrigation_amount: float = 20.0):
    # Only print and act if moisture is actually below the threshold
    if current_moisture < min_moisture:
        print(f"[CAMP MANAGER] Moisture level ({current_moisture}%) is below minimum ({min_moisture}%). Triggering automatic irrigation!", flush=True)
        await force_irrigation(mqtt_client, current_moisture, irrigation_amount)