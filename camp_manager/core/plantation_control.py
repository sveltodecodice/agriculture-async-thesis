import json

async def plant_seed(mqtt_client, user_selected_seed: dict = None, top_3_seeds: list = None):
    seed_to_plant = user_selected_seed
    
    if not seed_to_plant and top_3_seeds:
        seed_to_plant = top_3_seeds[0]
        
    if not seed_to_plant:
        print("[CAMP MANAGER] Error: No seed selected and no top seeds available.", flush=True)
        return False

    seed_name = seed_to_plant.get("name") if isinstance(seed_to_plant, dict) else str(seed_to_plant)
    payload = json.dumps({"plant_name": seed_name})
    
    await mqtt_client.publish("plantation/cmd/plant", payload=payload)
    print(f"[CAMP MANAGER] Dispatched PLANT command for: {seed_name}", flush=True)
    return True

async def clear_camp(mqtt_client):
    await mqtt_client.publish("plantation/cmd/clear", payload="trigger")
    
    empty_payload = {
        "camp_availability": False,
        "status_detail": {
            "plant_name": "None",
            "status": "EMPTY",
            "time_left": 0,
            "min_soilmoisture": 20.0
        }
    }
    await mqtt_client.publish("plantation/status", payload=json.dumps(empty_payload))
    print("[CAMP MANAGER] Dispatched CLEAR command and updated status to EMPTY.", flush=True)
    return True