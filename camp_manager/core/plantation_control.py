import json

async def plant_seed(mqtt, user_selected_seed, camp_id: str = "fortnite"):
    if isinstance(user_selected_seed, str):
        payload = json.dumps({"name": user_selected_seed.strip()})
    else:
        payload = json.dumps(user_selected_seed)

    topic = f"camp/{camp_id}/plantation/cmd/plant"
    await mqtt.publish(topic, payload)
    print(f"[CAMP MANAGER] [{camp_id.upper()}] Dispatched PLANT command for: {user_selected_seed.get('name') if isinstance(user_selected_seed, dict) else user_selected_seed}", flush=True)


async def clear_camp(mqtt, camp_id: str = "fortnite"):
    topic = f"camp/{camp_id}/plantation/cmd/clear"
    await mqtt.publish(topic, "trigger")
    print(f"[CAMP MANAGER] [{camp_id.upper()}] Dispatched CLEAR command.", flush=True)