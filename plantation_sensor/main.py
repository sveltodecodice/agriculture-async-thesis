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
from core.mqtt_utils import publish_json, Deduper

BROKER_IP = os.getenv("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))
broker_user = os.getenv("MQTT_BROKER_USER", "farm_admin")
broker_pass = os.getenv("MQTT_BROKER_PASS", "secure_farm")

node_state = {
    "moisture": None,
    "current_season": "winter"
}

# Istanza di dedup dedicata a questo servizio (non condividerla altrove,
# es. camp_manager e' sottoscritto agli stessi topic ma deve tenere la
# propria memoria separata)
dedup = Deduper()


async def monitor_loop(mqtt_client):
    while True:
        await asyncio.sleep(5)
        current_status = get_status(node_state["moisture"])

        # Always stringify JSON payload before sending, timestamped
        await publish_json(mqtt_client, "plantation/status", current_status)


async def start_node():
    while True:
        try:
            async with aiomqtt.Client(
                hostname=BROKER_IP,
                port=BROKER_PORT,
                username=broker_user,
                password=broker_pass
            ) as mqtt_client:
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

                        if dedup.is_duplicate_or_stale("camp/terrain_telemetry", packet.get("ts")):
                            continue

                        if "soil_moisture" in packet:
                            node_state["moisture"] = float(packet["soil_moisture"])

                    elif channel == "environment/telemetry":
                        packet = json.loads(raw_payload)

                        if dedup.is_duplicate_or_stale("environment/telemetry", packet.get("ts")):
                            continue

                        if "season" in packet:
                            node_state["current_season"] = packet.get("season", "winter")
                        # Advance internal plant growth timer by 1 day on each environment tick
                        advance_days(1)

                    # 3. HANDLE COMMANDS FROM CAMP MANAGER & DIRECT TOPICS
                    elif channel in ["camp_manager/commands", "plantation/cmd/clear", "plantation/cmd/reset", "plantation/cmd/plant"]:
                        try:
                            # Direct clear or reset commands
                            if channel in ["plantation/cmd/clear", "plantation/cmd/reset"]:
                                clear_field()
                                if channel == "plantation/cmd/reset":
                                    # Il reset invalida la storia dei ts: altrimenti un
                                    # messaggio legittimo post-reset potrebbe essere
                                    # scartato come "stale"
                                    dedup.reset()
                                print("[PLANTATION] Field status reset to vacant.", flush=True)
                                await publish_json(mqtt_client, "plantation/status", get_status(node_state["moisture"]))

                            # JSON command packets
                            else:
                                packet = json.loads(raw_payload)
                                action = packet.get("action")
                                if action == "PLANT":
                                    target_seed = packet.get("seed")
                                    if target_seed:
                                        seed_planted(target_seed)
                                        seed_name = target_seed.get('name') if isinstance(target_seed, dict) else target_seed
                                        print(f"[PLANTATION] Successfully sowed: {seed_name}", flush=True)
                                        await publish_json(mqtt_client, "plantation/status", get_status(node_state["moisture"]))
                                elif action in ["HARVEST", "CLEAR", "RESET"]:
                                    clear_field()
                                    print("[PLANTATION] Field cleared.", flush=True)
                                    await publish_json(mqtt_client, "plantation/status", get_status(node_state["moisture"]))
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