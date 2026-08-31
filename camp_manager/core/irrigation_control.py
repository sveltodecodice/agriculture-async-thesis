async def force_irrigation(mqtt_client, current_moisture: float, irrigation_amount: float = 15.0):
    print(f"[CAMP MANAGER] Publishing command to FORCE irrigate. (Current moisture: {current_moisture})")
    await mqtt_client.publish(
        topic="terrain/cmd/irrigate",
        payload=str(irrigation_amount)
    )

async def auto_irrigate(mqtt_client, current_moisture: float, irrigation_amount: float = 15.0):
    print(f"[CAMP MANAGER] Checking if auto-irrigation is needed for moisture: {current_moisture}")