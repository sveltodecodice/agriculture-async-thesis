import asyncio
import json
import os
import aiomqtt

# Import from your manager's core files
from core.plantation_control import plant_seed, clear_camp
from core.irrigation_control import force_irrigation
from core.time_control import force_skip_days
from core.seeds import list_seeds

broker_host = os.getenv('MQTT_BROKER_HOST', 'mqtt-broker')
broker_port = int(os.getenv('MQTT_BROKER_PORT', 1883))

# --- MASTER FARM STATE ---
farm_state = {
    "occupied": False,
    "empty_days": 0,
    "moisture": 50.0,
    "seed_name": None,
    "min_moisture": 0.0,
    "time_left": 0
}

async def auto_plant_monitor_loop(client):
    """Periodically checks if the field has been empty for 3 days and auto-plants."""
    while True:
        await asyncio.sleep(5)
        if not farm_state["occupied"]:
            if farm_state["empty_days"] >= 3:
                print("[CAMP MANAGER] 3-day timeout reached. Auto-planting top seed...", flush=True)
                top_seed = list_seeds[0]
                await plant_seed(client, user_selected_seed=top_seed)
                farm_state["empty_days"] = 0

async def listen_camp_commands(client: aiomqtt.Client):
    """Listens for manual commands and live sensor telemetry."""
    await client.subscribe("camp_manager/cmd/#")
    await client.subscribe("environment/skip_day")
    await client.subscribe("plantation/status")
    await client.subscribe("camp/terrain_telemetry") # Listen to terrain for auto-irrigation
    
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
            else:
                print(f"[ERROR] Seed '{payload}' not found in database.", flush=True)
                
        elif topic == "camp_manager/cmd/clear":
            await clear_camp(client)
            
        elif topic == "camp_manager/cmd/irrigate":
            await force_irrigation(client, farm_state["moisture"])
            
        elif "environment/skip_day" in topic:
            try:
                days = int(payload)
                # We REMOVED the force_skip_days call here so it stops talking to itself!
                
                # Just passively count the skipped days
                for _ in range(days):
                    if not farm_state["occupied"]:
                        farm_state["empty_days"] += 1
                
                if not farm_state["occupied"]:
                    print(f"[CAMP MANAGER] Fast-forwarded {days} days. Field vacant for {farm_state['empty_days']} days total.", flush=True)
            except ValueError:
                pass

# --- 2. HANDLE SENSOR TELEMETRY (THE "BRAIN") ---
        elif "environment/telemetry" in topic:
            try:
                data = json.loads(message.payload.decode('utf-8'))
                farm_state["season"] = data.get("season", farm_state["season"])
                
                # THE FIX: Count natural days passing!
                # Every time the ambient sensor ticks, 1 day has passed in the simulation.
                if not farm_state["occupied"]:
                    farm_state["empty_days"] += 1
                    print(f"[CAMP MANAGER] Natural day passed. Field vacant for {farm_state['empty_days']} days.", flush=True)
                else:
                    farm_state["empty_days"] = 0
                    
            except Exception:
                pass

        elif "camp/terrain_telemetry" in topic:
            try:
                data = json.loads(message.payload.decode('utf-8'))
                farm_state["moisture"] = data.get("soil_moisture", 50.0)
                
                # Auto-Irrigation Check!
                if farm_state["occupied"]:
                    if farm_state["moisture"] < farm_state["min_moisture"]:
                        print(f"[AUTO-IRRIGATE] {farm_state['seed_name']} is too dry ({farm_state['moisture']}% < {farm_state['min_moisture']}%). Watering field!", flush=True)
                        await force_irrigation(client, farm_state["moisture"])
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