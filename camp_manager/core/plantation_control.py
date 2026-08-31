import json

async def plant_seed(mqtt_client, user_selected_seed: dict = None, top_3_seeds: list = None):
    """Sends the plant command via MQTT to the plantation sensor."""
    seed_to_plant = user_selected_seed
    if not seed_to_plant and top_3_seeds:
        seed_to_plant = top_3_seeds[0]

    if seed_to_plant:
        # Format payload to match what plantation sensor expects
        payload = json.dumps({"action": "PLANT", "seed": seed_to_plant})
        await mqtt_client.publish("camp_manager/commands", payload=payload)
        print(f"[CAMP MANAGER] Dispatched PLANT command for: {seed_to_plant['name']}")
        return True
    return False

async def clear_camp(mqtt_client):
    """Sends the clear/harvest command via MQTT to the plantation sensor."""
    payload = json.dumps({"action": "HARVEST"})
    await mqtt_client.publish("camp_manager/commands", payload=payload)
    print("[CAMP MANAGER] Dispatched HARVEST command to clear camp.")