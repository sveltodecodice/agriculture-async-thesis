import asyncio
import json
import os
import aiomqtt

from core.plant_conditions import seed_planted, clear_field, advance_days, get_status
from core.seeds import list_seeds

BROKER_IP = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

node_state = {
    "moisture": None,
    "current_season": "winter"
}

async def monitor_loop(mqtt_client):
    while True:
        await asyncio.sleep(8)
        try:
            current_level = node_state["moisture"]
            current_status = get_status(current_level)
            
            if current_status["camp_availability"]:
                crop_info = current_status["status_detail"]
                print(f"[PLANTATION] Active Crop: {crop_info['plant_name']} | Remaining: {crop_info['time_left']}d | Health: {crop_info['health']}", flush=True)
                
                lower_bound = crop_info.get("min_soilmoisture")
                upper_bound = crop_info.get("max_soilmoisture")
                
                if current_level is not None and current_level < lower_bound:
                    print(f"[PLANTATION] Moisture {current_level}% breached lower threshold {lower_bound}%. Requesting irrigation.", flush=True)
                    await mqtt_client.publish("terrain/cmd/irrigate", payload="15.0")
            else:
                print("[PLANTATION] Field status: vacant", flush=True)

            await mqtt_client.publish("plantation/status", payload=json.dumps(current_status))
        except Exception as err:
            print(f"[PLANTATION ERROR] Loop exception: {err}", flush=True)

async def start_node():
    while True:
        try:
            async with aiomqtt.Client(hostname=BROKER_IP, port=BROKER_PORT) as mqtt_client:
                # 1. FIX THE SUBSCRIPTIONS HERE
                await mqtt_client.subscribe("environment/telemetry")
                await mqtt_client.subscribe("camp/terrain_telemetry")
                await mqtt_client.subscribe("camp_manager/commands")
                
                print("Plantation subsystem online.", flush=True)
                asyncio.create_task(monitor_loop(mqtt_client))

                async for incoming in mqtt_client.messages:
                    channel = str(incoming.topic)
                    raw_payload = incoming.payload.decode()
                    
                    # 2. FIX THE TERRAIN TOPIC AND PAYLOAD KEY HERE
                    if "camp/terrain_telemetry" in channel:
                        packet = json.loads(raw_payload)
                        # The terrain sensor sends "soil_moisture", not "moisture"
                        if "soil_moisture" in packet:
                            node_state["moisture"] = float(packet["soil_moisture"])
                            
                    # 3. FIX THE AMBIENT TOPIC HERE
                    elif "environment/telemetry" in channel:
                        packet = json.loads(raw_payload)
                        if "season" in packet:
                            node_state["current_season"] = packet.get("season", "winter")
                        # Advance internal counter by 1 day on ambient tick
                        advance_days(1)
                            
                    elif "camp_manager/commands" in channel:
                        try:
                            packet = json.loads(raw_payload)
                            if packet.get("action") == "PLANT":
                                target_seed = packet.get("seed")
                                if target_seed:
                                    seed_planted(target_seed)
                                    print(f"[PLANTATION] Successfully sowed: {target_seed.get('name')}", flush=True)
                            elif packet.get("action") == "HARVEST":
                                clear_field()
                                print("[PLANTATION] Field cleared.", flush=True)
                        except Exception:
                            pass
        except aiomqtt.MqttError:
            print("Broker link lost. Reconnecting...", flush=True)
            await asyncio.sleep(4)
        except Exception as ex:
            print(f"Critical fault: {ex}", flush=True)
            await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(start_node())
    except KeyboardInterrupt:
        pass