import json

async def plant_seed(mqtt_client, user_selected_seed: dict = None, top_3_seeds: list = None):
    seed_to_plant = user_selected_seed
    
    if not seed_to_plant and top_3_seeds:
        seed_to_plant = top_3_seeds[0]
        
    if not seed_to_plant:
        print("[CAMP MANAGER] Error: No seed selected and no top seeds available.", flush=True)
        return False

    seed_name = seed_to_plant.get("name") if isinstance(seed_to_plant, dict) else str(seed_to_plant)
    
    payload = json.dumps({
        "action": "PLANT",
        "seed": seed_to_plant
    })
    
    #await mqtt_client.publish("camp_manager/commands", payload=payload)            #eliminata x duplicazione doppia chiamata 
    await mqtt_client.publish("plantation/cmd/plant", payload=payload)
    print(f"[CAMP MANAGER] Dispatched PLANT command for: {seed_name}", flush=True)
    return True

async def clear_camp(mqtt_client):
    payload = json.dumps({"action": "CLEAR"})
    #await mqtt_client.publish("camp_manager/commands", payload=payload)                #eliminata x duplicazione doppia chiamata 
    await mqtt_client.publish("plantation/cmd/clear", payload="trigger")
    print("[CAMP MANAGER] Dispatched CLEAR command.", flush=True)
    return True

async def reset_camp(mqtt_client):
    payload = json.dumps({"action": "RESET"})
    #await mqtt_client.publish("camp_manager/commands", payload=payload)                #eliminata x duplicazione doppia chiamata 
    await mqtt_client.publish("plantation/cmd/reset", payload="trigger")
    print("[CAMP MANAGER] Dispatched RESET command.", flush=True)
    return True