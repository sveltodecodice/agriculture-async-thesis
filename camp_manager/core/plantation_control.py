import json

async def plant_seed(mqtt, user_selected_seed):
    if isinstance(user_selected_seed, str):
        payload = json.dumps({"name": user_selected_seed.strip()})
    else:
        payload = json.dumps(user_selected_seed)

    await mqtt.publish("plantation/cmd/plant", payload)
    print(f"[CAMP MANAGER] Dispatched PLANT command for: {user_selected_seed.get('name') if isinstance(user_selected_seed, dict) else user_selected_seed}", flush=True)


async def clear_camp(mqtt):
    await mqtt.publish("plantation/cmd/clear", "trigger")
    print("[CAMP MANAGER] Dispatched CLEAR command.", flush=True)