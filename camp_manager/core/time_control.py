import json
import asyncio


async def force_skip_days(mqtt_client, days_to_skip: int, farm_state: dict = None):
    if not (1 <= days_to_skip <= 30):
        print("[WARNING] Days to skip must be between 1 and 30.", flush=True)
        return False
    
    await mqtt_client.publish(
        topic="environment/skip_day",
        payload=str(days_to_skip)
    )
    print(f"[CAMP MANAGER] Requested to skip {days_to_skip} days.", flush=True)

    return True