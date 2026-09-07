import json
import asyncio
from core.irrigation_control import auto_irrigate

async def force_skip_days(mqtt_client, days_to_skip: int, farm_state: dict = None):
    if not (1 <= days_to_skip <= 30):
        print("[WARNING] Days to skip must be between 1 and 30.", flush=True)
        return False
    
    await mqtt_client.publish(
        topic="environment/skip_day",
        payload=str(days_to_skip)
    )
    print(f"[CAMP MANAGER] Requested to skip {days_to_skip} days.", flush=True)

    if farm_state and farm_state.get("occupied"):
        min_moisture = farm_state.get("min_moisture", 20.0)
        current_moisture = farm_state.get("moisture", 50.0)
        
        for day in range(days_to_skip):
            current_moisture -= 3.0
            if current_moisture < min_moisture:
                log_msg = f"💧 Day {day + 1}/{days_to_skip}: Moisture hit {current_moisture:.1f}%. Auto-irrigating!"
                print(f"[CAMP MANAGER] {log_msg}", flush=True)
                await mqtt_client.publish("camp/notifications", log_msg)
                
                await auto_irrigate(mqtt_client, current_moisture, min_moisture=min_moisture, irrigation_amount=25.0)
                current_moisture += 25.0

    return True