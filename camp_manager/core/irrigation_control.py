import json

async def force_irrigation(mqtt_client, current_moisture: float = 0.0, irrigation_amount: float = 25.0, camp_id: str = "campo_1"):
    print(f"[CAMP MANAGER] [{camp_id.upper()}] Publishing FORCE irrigate. (Current moisture: {current_moisture}%)", flush=True)
    payload = str(irrigation_amount)
    topic = f"camp/{camp_id}/terrain/cmd/irrigate"
    await mqtt_client.publish(topic, payload)

async def auto_irrigate(mqtt_client, current_moisture: float, min_moisture: float = 20.0, irrigation_amount: float = 13.0, camp_id: str = "campo_1"):
    minimal_moisture = max(min_moisture, 20.0)
    if current_moisture <= minimal_moisture:
        print(f"[CAMP MANAGER] [{camp_id.upper()}] Moisture level ({current_moisture}%) fell below minimum ({minimal_moisture}%). Auto-irrigating!", flush=True)
        await force_irrigation(mqtt_client, current_moisture, irrigation_amount, camp_id=camp_id)