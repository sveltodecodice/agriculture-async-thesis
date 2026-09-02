import json
from core.harvest_deposit import record_harvest
from core.plantation_control import clear_camp

async def process_plantation_status(farm_state: dict, client, payload_bytes: bytes):
    """Processes incoming plantation telemetry and triggers automated harvest."""
    try:
        data = json.loads(payload_bytes.decode('utf-8'))
        farm_state["occupied"] = bool(data.get("camp_availability", False))
        
        detail = data.get("status_detail") or {}
        farm_state["seed_name"] = detail.get("plant_name")
        farm_state["time_left"] = detail.get("time_left", 0)
        farm_state["min_moisture"] = detail.get("min_soilmoisture", 0.0)

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

    except Exception:
        pass