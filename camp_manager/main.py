import asyncio 
import json 
import os
import aiomqtt

from core.plantation_control import plant_seed, clear_camp
from core.irrigation_control import force_irrigation, auto_irrigate
from core.time_control import force_skip_days
from core.seeds import list_seeds
from core.harvest_deposit import save_harvest, get_harvest_history, FILE_PATH
from core.seed_matcher import find_top_3_seeds
from core.logger import log_event, get_logs, clear_logs


broker_host = os.getenv('MQTT_BROKER_HOST', 'mqtt-broker')
broker_port = int(os.getenv('MQTT_BROKER_PORT', 1883))
broker_user = os.getenv("MQTT_BROKER_USER", "farm_admin")
broker_pass = os.getenv("MQTT_BROKER_PASS", "secure_farm")

farm_state = {
    "occupied": False,
    "empty_days": 0,
    "moisture": 50.0,
    "oxygenation": 70.0,
    "temperature": 20,
    "weather": "Sunny",
    "irrigation_active": False,
    "season": "winter",
    "date": "01/01/2026",
    "last_log_date": None,
    "seed_name": None,
    "min_moisture": 20.0,
    "max_moisture": 80.0,
    "time_left": 0,
    "harvest_pending": False,
}

async def auto_plant_monitor_loop(client):
    while True:
        await asyncio.sleep(5)
        if not farm_state["occupied"]:
            if farm_state["empty_days"] >= 3:
                current_season = farm_state.get("season", "spring")
                top_seeds = find_top_3_seeds(farm_state["moisture"], current_season)
                target_seed = top_seeds[0] if top_seeds else list_seeds[0]
                
                log_msg = f"Field vacant for 3 days. Auto-planted {target_seed['name']}."
                print(f"[CAMP MANAGER] {log_msg}", flush=True)
                await client.publish("camp/notifications", log_msg)
                
                await plant_seed(client, user_selected_seed=target_seed)
                farm_state["empty_days"] = 0
                farm_state["occupied"] = True
                
                logs = log_event("AUTO_PLANT", f"Auto-planted {target_seed['name']}", farm_state.get("date"), stats=farm_state)
                await client.publish("camp/activity_logs", json.dumps(logs))

async def handle_system_reset(client):
    try:
        with open(FILE_PATH, "w") as f:
            json.dump([], f)
        
        farm_state.update({
            "occupied": False, "empty_days": 0, "moisture": 60.0, "oxygenation": 70.0,
            "temperature": 20, "weather": "Sunny", "irrigation_active": False,
            "season": "winter", "date": "01/01/2026", "last_log_date": None,
            "seed_name": None, "min_moisture": 20.0, "max_moisture": 80.0,
            "time_left": 0, "harvest_pending": False,
        })

        clear_logs()
        await clear_camp(client)
        await client.publish("camp/harvest_deposit", "Harvest Deposit: Empty")
        await client.publish("camp/activity_logs", json.dumps([]))
        await client.publish("environment/cmd/reset", "01/01/2026")
        await client.publish("terrain/cmd/reset", "trigger")
        await client.publish("plantation/cmd/reset", "trigger")
        
        await client.publish("camp/notifications", "🔄 System reset complete.")
        print("[CAMP MANAGER] Full system reset complete.", flush=True)
    except Exception as e:
        print(f"[ERROR] Reset failed: {e}", flush=True)

async def process_plantation_status(client, payload_bytes):
    try:
        data = json.loads(payload_bytes.decode('utf-8'))
        
        detail = data.get("status_detail") or {}
        plant_name = detail.get("plant_name") if isinstance(detail, dict) else None
        
        if not data.get("camp_availability", False) or not plant_name or plant_name == "None":
            farm_state["occupied"] = False
            farm_state["seed_name"] = None
            farm_state["harvest_pending"] = False
            return

        farm_state["occupied"] = True
        farm_state["empty_days"] = 0
        farm_state["seed_name"] = plant_name
        farm_state["time_left"] = detail.get("time_left", 0)
        farm_state["min_moisture"] = detail.get("min_soilmoisture", 20.0)

        if farm_state["occupied"] and farm_state["time_left"] <= 0 and not farm_state["harvest_pending"]:
            farm_state["harvest_pending"] = True
            
            log_msg = f"{farm_state['seed_name']} growth complete! Auto-harvesting..."
            print(f"[CAMP MANAGER] {log_msg}", flush=True)
            await client.publish("camp/notifications", log_msg)
            
            updated_history = save_harvest(farm_state["seed_name"], farm_state.get("date"))
            await client.publish("camp/harvest_deposit", payload=json.dumps(updated_history))
            
            logs = log_event("AUTO_HARVEST", f"Harvested {farm_state['seed_name']}", farm_state.get("date"), stats=farm_state)
            await client.publish("camp/activity_logs", json.dumps(logs))
            
            await clear_camp(client)
            farm_state["occupied"] = False
            farm_state["seed_name"] = None

    except Exception as e:
        print(f"[ERROR] Plantation status error: {e}", flush=True)
        
async def listen_camp_commands(client: aiomqtt.Client):
    await client.subscribe("camp_manager/cmd/#")
    await client.subscribe("environment/telemetry")
    await client.subscribe("plantation/status")
    await client.subscribe("camp/terrain_telemetry")
    
    print("[CAMP MANAGER] Listening for commands and telemetry...", flush=True)
    
    history = get_harvest_history()
    history_payload = json.dumps(history) if history else "🌾 Harvest Deposit: Empty"
    await client.publish("camp/harvest_deposit", history_payload)
    await client.publish("camp/activity_logs", json.dumps(get_logs()))
    
    async for message in client.messages:
        topic = str(message.topic)
        raw_payload = message.payload.decode('utf-8').strip() if isinstance(message.payload, bytes) else str(message.payload).strip()
        payload_lower = raw_payload.lower()
        
        if topic in ["camp_manager/cmd/reset", "camp_manager/cmd/restart"]:
            await handle_system_reset(client)

        elif topic == "camp_manager/cmd/plant":
            selected_seed = next((s for s in list_seeds if s["name"].lower() == payload_lower), None)
            if selected_seed:
                await plant_seed(client, user_selected_seed=selected_seed)
                farm_state["empty_days"] = 0
                farm_state["occupied"] = True
                farm_state["harvest_pending"] = False
                
                logs = log_event("PLANTED", f"Planted {selected_seed['name']}", farm_state.get("date"), stats=farm_state)
                await client.publish("camp/activity_logs", json.dumps(logs))
                
        elif topic == "camp_manager/cmd/clear":
            await clear_camp(client)
            farm_state["occupied"] = False
            farm_state["seed_name"] = None
            farm_state["harvest_pending"] = False
            farm_state["empty_days"] = 0
            
            logs = log_event("CLEARED", "Field cleared", farm_state.get("date"), stats=farm_state)
            await client.publish("camp/activity_logs", json.dumps(logs))
            
        elif topic == "camp_manager/cmd/irrigate":
            await force_irrigation(client, farm_state["moisture"])
            logs = log_event("IRRIGATED", "Field manually irrigated", farm_state.get("date"), stats=farm_state)
            await client.publish("camp/activity_logs", json.dumps(logs))

        elif topic == "camp_manager/cmd/reoxygenate":
            await client.publish("terrain/cmd/reoxygenate", "trigger")
            await client.publish("camp/notifications", "💨 Soil manually reoxygenated.")
            
        elif topic == "camp_manager/cmd/skip":
            try:
                try:
                    days = int(raw_payload)
                except ValueError:
                    days = int(json.loads(raw_payload).get("days", 1))
                
                await force_skip_days(client, days, farm_state)
                if not farm_state["occupied"]:
                    farm_state["empty_days"] += days
            except Exception:
                pass

        elif "environment/telemetry" in topic:
            try:
                data = json.loads(raw_payload)
                farm_state["season"] = data.get("season", farm_state["season"]) 
                farm_state["date"] = data.get("date", farm_state.get("date"))
                farm_state["temperature"] = data.get("temperature", farm_state.get("temperature", 20))
                farm_state["weather"] = data.get("weather", farm_state.get("weather", "Sunny"))
                
                if not farm_state["occupied"]:
                    farm_state["empty_days"] += 1
                else:
                    farm_state["empty_days"] = 0
            except Exception:
                pass
            
        elif "plantation/status" in topic:
            await process_plantation_status(client, message.payload)

        elif "camp/terrain_telemetry" in topic:
            try:
                data = json.loads(raw_payload)
                farm_state["moisture"] = data.get("soil_moisture", 50.0)
                farm_state["oxygenation"] = data.get("oxygenation", 70.0)
                farm_state["irrigation_active"] = data.get("irrigation_active", False)
                farm_state["date"] = data.get("date", farm_state.get("date"))
                
                # Trigger DAILY_SNAPSHOT here where environment and terrain metrics are fully synchronized
                if farm_state["date"] != farm_state["last_log_date"]:
                    farm_state["last_log_date"] = farm_state["date"]
                    logs = log_event("DAILY_SNAPSHOT", "Daily Farm Status", farm_state["date"], stats=farm_state)
                    await client.publish("camp/activity_logs", json.dumps(logs))

                top_seeds = find_top_3_seeds(farm_state["moisture"], farm_state.get("season", "spring"))
                top_names = [s["name"].capitalize() for s in top_seeds[:3]]
                await client.publish("camp/top_seeds", "Top 3 Seeds: " + ", ".join(top_names))

                target_min = farm_state["min_moisture"] if farm_state["occupied"] else 20.0
                
                if farm_state["moisture"] <= max(target_min, 20.0) and not farm_state["irrigation_active"]:
                    await auto_irrigate(client, current_moisture=farm_state["moisture"], min_moisture=target_min)
                    await client.publish("camp/notifications", f"💧 Auto-irrigating! Moisture at {farm_state['moisture']}%.")
                    logs = log_event("AUTO_IRRIGATE", "Triggered auto-irrigation", farm_state.get("date"), stats=farm_state)
                    await client.publish("camp/activity_logs", json.dumps(logs))
                    
                if farm_state["oxygenation"] < 30.0:
                    await client.publish("terrain/cmd/reoxygenate", "trigger")
                    await client.publish("camp/notifications", f"💨 Auto-oxygenating! Level at {farm_state['oxygenation']}%.")
                    logs = log_event("AUTO_OXYGENATE", "Triggered auto-oxygenation", farm_state.get("date"), stats=farm_state)
                    await client.publish("camp/activity_logs", json.dumps(logs))
            except Exception:
                pass

async def main():
    print("[CAMP MANAGER] Starting up...", flush=True)
    while True:
        try:
            async with aiomqtt.Client(hostname=broker_host, port=broker_port, username=broker_user, password=broker_pass) as client:
                asyncio.create_task(listen_camp_commands(client))
                asyncio.create_task(auto_plant_monitor_loop(client))
                while True:
                    await asyncio.sleep(10)
        except Exception:
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())