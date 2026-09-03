import json
from core.harvest_deposit import record_harvest
from core.plantation_control import clear_camp

async def process_plantation_status(client, payload_bytes):
    """Processes incoming plantation telemetry and triggers automated harvest."""
    try:
        data = json.loads(payload_bytes.decode('utf-8'))
        farm_state["occupied"] = bool(data.get("camp_availability", False))
        
        detail = data.get("status_detail") or {}
        farm_state["seed_name"] = detail.get("plant_name")
        farm_state["time_left"] = detail.get("time_left", 0)
        farm_state["min_moisture"] = detail.get("min_soilmoisture", 0.0)

        # Check for auto-irrigation directly when plantation reports status
        if farm_state["occupied"] and not farm_state["harvest_pending"]:
            await auto_irrigate(
                client, 
                current_moisture=farm_state["moisture"], 
                min_moisture=farm_state["min_moisture"]
            )

        is_ready = farm_state["occupied"] and farm_state["time_left"] <= 0
        can_harvest = is_ready and farm_state["seed_name"] and not farm_state["harvest_pending"]

        if can_harvest:
            farm_state["harvest_pending"] = True
            print(f"[CAMP MANAGER] {farm_state['seed_name']} finished growing. Harvesting...", flush=True)
            record_harvest(farm_state["seed_name"], farm_state.get("date"))
            await clear_camp(client)
            farm_state["empty_days"] = 0

        if not farm_state["occupied"]:
            farm_state["harvest_pending"] = False

    except Exception as e:
        print(f"[ERROR] Plantation status processing failed: {e}", flush=True)