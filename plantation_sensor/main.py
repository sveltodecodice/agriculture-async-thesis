import asyncio
import json
import os
import aiomqtt

# Import core functions
from core.plant_conditions import (
    seed_planted,
    clear_field,
    advance_days,
    get_status,
)

BROKER_IP = os.getenv("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

node_state = {
    "moisture": None,
    "current_season": "winter"
}

async def monitor_loop(mqtt_client):
    while True:
        await asyncio.sleep(5)
        current_status = get_status(node_state["moisture"])
        
        # Publish current plantation status telemetry to Camp Manager
        await mqtt_client.publish("plantation/status", payload=json.dumps(current_status))


async def start_node():
    while True:
        try:
            async with aiomqtt.Client(hostname=BROKER_IP, port=BROKER_PORT) as mqtt_client:
                # 1. SUBSCRIPTIONS
                await mqtt_client.subscribe("environment/telemetry")
                await mqtt_client.subscribe("camp/terrain_telemetry")
                await mqtt_client.subscribe("camp_manager/commands")
                await mqtt_client.subscribe("plantation/cmd/#")
                
                print("Plantation subsystem online.", flush=True)
                asyncio.create_task(monitor_loop(mqtt_client))

                async for incoming in mqtt_client.messages:
                    channel = str(incoming.topic)
                    raw_payload = incoming.payload.decode()

                    # 2. HANDLE TELEMETRY
                    if channel == "camp/terrain_telemetry":
                        packet = json.loads(raw_payload)
                        if "soil_moisture" in packet:
                            node_state["moisture"] = float(packet["soil_moisture"])

                    elif channel == "environment/telemetry":
                        packet = json.loads(raw_payload)
                        if "season" in packet:
                            node_state["current_season"] = packet.get("season", "winter")
                        # Advance internal plant growth timer by 1 day on each environment tick
                        advance_days(1)

                    # 3. HANDLE COMMANDS FROM CAMP MANAGER
                    elif channel in ["camp_manager/commands", "plantation/cmd/clear"]:
                        try:
                            # Handle string commands directly
                            if raw_payload == "trigger" or channel == "plantation/cmd/clear":
                                clear_field()
                                print("[PLANTATION] Field status reset to vacant.", flush=True)
                                continue

                            # Handle JSON command packets
                            packet = json.loads(raw_payload)
                            if packet.get("action") == "PLANT":
                                target_seed = packet.get("seed")
                                if target_seed:
                                    seed_planted(target_seed)
                                    print(f"[PLANTATION] Successfully sowed: {target_seed.get('name')}", flush=True)
                            elif packet.get("action") in ["HARVEST", "CLEAR"]:
                                clear_field()
                                print("[PLANTATION] Field cleared.", flush=True)
                        except Exception as err:
                            print(f"[PLANTATION ERROR] Command handling error: {err}", flush=True)

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