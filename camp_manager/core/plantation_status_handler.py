import json
from core.harvest_deposit import save_harvest
from core.plantation_control import clear_camp
from core.irrigation_control import auto_irrigate

async def process_plantation_status(client, payload_bytes):
    try:
        data = json.loads(payload_bytes.decode('utf-8'))
        
        detail = data.get("status_detail") or {}
        plant_name = detail.get("plant_name") if isinstance(detail, dict) else None
        
        # If no plant is active, set occupied to False WITHOUT zeroing empty_days
        if not data.get("camp_availability", False) or not plant_name or plant_name == "None":
            farm_state["occupied"] = False
            farm_state["seed_name"] = None
            farm_state["harvest_pending"] = False
            return

        farm_state["occupied"] = True
        farm_state["seed_name"] = plant_name
        farm_state["time_left"] = detail.get("time_left", 0)
        farm_state["min_moisture"] = detail.get("min_soilmoisture", 20.0)

        if farm_state["occupied"] and farm_state["time_left"] <= 0 and not farm_state["harvest_pending"]:
            farm_state["harvest_pending"] = True
            
            log_msg = f"🎉 {farm_state['seed_name']} growth complete! Auto-harvesting..."
            print(f"[CAMP MANAGER] {log_msg}", flush=True)
            await client.publish("camp/notifications", log_msg)
            
            updated_history = save_harvest(farm_state["seed_name"], farm_state.get("date"))
            await client.publish("camp/harvest_deposit", payload=json.dumps(updated_history))
            
            logs = log_event("HARVESTED", f"Harvested {farm_state['seed_name']}", farm_state.get("date"))
            await client.publish("camp/activity_logs", json.dumps(logs))
            
            await clear_camp(client)
            farm_state["occupied"] = False
            farm_state["seed_name"] = None

    except Exception as e:
        print(f"[ERROR] Plantation status error: {e}", flush=True)