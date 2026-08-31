import json

async def force_skip_days(mqtt_client, days_to_skip: int):
    """
    Forces the ambient sensor to skip n days (max 30).
    """
    if not (1 <= days_to_skip <= 30):
        print("[WARNING] Days to skip must be between 1 and 30.")
        return False
    
    # Publishes the integer payload to the topic the ambient sensor listens to
    await mqtt_client.publish(
        topic="environment/skip_day",
        payload=str(days_to_skip)
    )
    print(f"[CAMP MANAGER] Requested to skip {days_to_skip} days.")
    return True