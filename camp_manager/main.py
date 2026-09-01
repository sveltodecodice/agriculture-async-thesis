import asyncio
import json
import os
import aiomqtt

# Import from your manager's core files
from core.plantation_control import plant_seed, clear_camp
from core.irrigation_control import force_irrigation
from core.time_control import force_skip_days
from core.seeds import list_seeds
from core.harvest_deposit import record_harvest
from core.seed_matcher import find_seasonal_seeds

broker_host = os.getenv('MQTT_BROKER_HOST', 'mqtt-broker')
broker_port = int(os.getenv('MQTT_BROKER_PORT', 1883))

# --- MASTER FARM STATE ---
farm_state = {
    "occupied": False,
    "empty_days": 0,
    "moisture": 0.0,
    "season": "winter",
    "date": None,
    "seed_name": None,
    "min_moisture": 0.0,
    "time_left": 0,
    "harvest_pending": False,
}

async def auto_plant_monitor_loop(client):
    """Periodically checks if the field has been empty for 3 days and auto-plants."""
    while True:
        await asyncio.sleep(5)
        if not farm_state["occupied"]:
            if farm_state["empty_days"] >= 3:
                current_season = farm_state.get("season", "spring")
                print(f"[CAMP MANAGER] 3-day timeout reached. Auto-planting best seed for {current_season}...", flush=True)
                
                top_seeds = find_seasonal_seeds(current_season)
                target_seed = top_seeds[0] if top_seeds else list_seeds[0]
                
                await plant_seed(client, user_selected_seed=target_seed)
                farm_state["empty_days"] = 0

async def process_plantation_status(client, payload_bytes):
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

async def listen_camp_commands(client: aiomqtt.Client):
    """Listens for manual commands and live sensor telemetry."""
    await client.subscribe("camp_manager/cmd/#")
    await client.subscribe("environment/skip_day")
    await client.subscribe("environment/telemetry")
    await client.subscribe("plantation/status")
    await client.subscribe("camp/terrain_telemetry")
    
    print("[CAMP MANAGER] Listening for commands and telemetry...", flush=True)
    
    async for message in client.messages:
        topic = str(message.topic)
        payload = message.payload.decode('utf-8').strip().lower()
        
        # --- 1. HANDLE MANUAL TERMINAL COMMANDS ---
        if topic == "camp_manager/cmd/plant":
            selected_seed = next((s for s in list_seeds if s["name"] == payload), None)
            if selected_seed:
                await plant_seed(client, user_selected_seed=selected_seed)
                farm_state["empty_days"] = 0
                farm_state["harvest_pending"] = False
            else:
                print(f"[ERROR] Seed '{payload}' not found in database.", flush=True)
                
        elif topic == "camp_manager/cmd/clear":
            seed_being_cleared = farm_state["seed_name"]
            await clear_camp(client)
            if seed_being_cleared:
                record_harvest(seed_being_cleared, farm_state.get("date"))
            
        elif topic == "camp_manager/cmd/irrigate":
            await force_irrigation(client, farm_state["moisture"])
            
        elif "environment/skip_day" in topic:
            try:
                days = int(payload)
                print(f"[CAMP MANAGER] Skip of {days} day(s) requested.", flush=True)
            except ValueError:
                pass

        # --- 2. HANDLE SENSOR TELEMETRY (THE "BRAIN") ---
        elif "environment/telemetry" in topic:
            try:
                data = json.loads(message.payload.decode('utf-8'))
                farm_state["season"] = data.get("season", farm_state["season"])
                farm_state["date"] = data.get("date", farm_state.get("date"))
                
                if not farm_state["occupied"]:
                    farm_state["empty_days"] += 1
                    print(f"[CAMP MANAGER] Natural day passed. Field vacant for {farm_state['empty_days']} days.", flush=True)
                else:
                    farm_state["empty_days"] = 0
            except Exception:
                pass
            
        elif "plantation/status" in topic:
            await process_plantation_status(client, message.payload)

        elif "camp/terrain_telemetry" in topic:
            try:
                data = json.loads(message.payload.decode('utf-8'))
                farm_state["moisture"] = data.get("soil_moisture", 50.0)
                farm_state["date"] = data.get("date", farm_state.get("date"))
            except Exception:
                pass


async def main():
    """Main loop for the Camp Manager."""
    print("[CAMP MANAGER] Starting up...", flush=True)
    while True:
        try:
            async with aiomqtt.Client(hostname=broker_host, port=broker_port) as client:
                asyncio.create_task(listen_camp_commands(client))
                asyncio.create_task(auto_plant_monitor_loop(client))
                while True:
                    await asyncio.sleep(10)
        except Exception as e:
            print(f"[CAMP MANAGER] Connection error ({e}). Retrying in 5s...", flush=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[CAMP MANAGER] Stopped manually.", flush=True)