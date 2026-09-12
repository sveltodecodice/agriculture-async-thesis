import asyncio
import json
import ssl
import aiomqtt

from core.communication_par_man import (
    ACTIVITY_LOGS_TOPIC,
    HARVEST_DEPOSIT_TOPIC,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    NOTIFICATIONS_TOPIC,
)
from core.harvest_deposit import save_harvest
from core.logger import log_event
from core.plantation_control import clear_camp, plant_seed
from core.seed_matcher import find_top_3_seeds
from core.seeds import list_seeds

KNOWN_CAMPS = ["campo_1", "campo_2", "campo_3"]

SEED_TARGETS = {
    "wheat": 18.0, "grano": 18.0,
    "corn": 22.0, "mais": 22.0,
    "potato": 23.0, "patate": 23.0,
    "carrot": 24.0, "carote": 24.0,
    "tomato": 25.0, "pomodoro": 25.0,
    "zucchini": 26.0, "zucchine": 26.0,
    "lettuce": 28.0, "insalata": 28.0,
    "spinach": 30.0, "spinaci": 30.0,
    "sunflower": 20.0, "girasole": 20.0,
}


def create_default_state():
    return {
        "occupied": False,
        "empty_days": 0,
        "moisture": 28.0,
        "oxygenation": 70.0,
        "temperature": 20,
        "weather": "Sunny",
        "irrigation_active": False,
        "season": "winter",
        "date": "01/01/2026",
        "seed_name": None,
        "min_moisture": 18.0,
        "time_left": 0,
        "harvest_pending": False,
        "soil_type": "Franco",
        "water_dispensed_mm": 0.0,
    }


async def auto_plant_monitor_loop(mqtt, camp_id, state):
    while True:
        await asyncio.sleep(4)
        if state["occupied"]:
            continue

        season = state.get("season", "spring")
        top_seeds = find_top_3_seeds(state["moisture"], season)
        target = top_seeds[0] if top_seeds else list_seeds[0]

        log_msg = f"[{camp_id.upper()}] Campo libero. Autosemina avviata: {target['name'].capitalize()}."
        print(f"[CAMP MANAGER] {log_msg}", flush=True)
        await mqtt.publish(NOTIFICATIONS_TOPIC, log_msg)

        await plant_seed(mqtt, user_selected_seed=target, camp_id=camp_id)
        state["empty_days"] = 0
        state["occupied"] = True
        state["seed_name"] = target["name"].capitalize()

        logs = log_event("AUTO_PLANT", f"[{camp_id}] Autoseminato {target['name']}", state.get("date"), stats=state)
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))


async def process_plantation_status(mqtt, camp_id, payload_bytes, state):
    try:
        data = json.loads(payload_bytes.decode("utf-8"))
        detail = data.get("status_detail") or {}
        plant_name = detail.get("plant_name") if isinstance(detail, dict) else None

        if not data.get("camp_availability", False) or not plant_name or plant_name in ("None", "Unknown"):
            state["occupied"] = False
            state["seed_name"] = None
            state["harvest_pending"] = False
            state["min_moisture"] = 18.0
            return

        state["occupied"] = True
        state["empty_days"] = 0
        state["seed_name"] = plant_name
        state["time_left"] = detail.get("time_left", 0)

        clean_name = str(plant_name).lower()
        state["min_moisture"] = SEED_TARGETS.get(clean_name, 18.0)

        if not (state["occupied"] and state["time_left"] <= 0 and not state["harvest_pending"]):
            return

        state["harvest_pending"] = True
        log_msg = f"[{camp_id.upper()}] {state['seed_name']} maturazione completata! Auto-raccolto in corso..."
        print(f"[CAMP MANAGER] {log_msg}", flush=True)
        await mqtt.publish(NOTIFICATIONS_TOPIC, log_msg)

        history = save_harvest(state["seed_name"], state.get("date"))
        await mqtt.publish(HARVEST_DEPOSIT_TOPIC, json.dumps(history))

        logs = log_event("AUTO_HARVEST", f"[{camp_id}] Raccolto {state['seed_name']}", state.get("date"), stats=state)
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))

        await clear_camp(mqtt, camp_id=camp_id)
        
        state["occupied"] = False
        state["seed_name"] = None
        state["harvest_pending"] = False
    except Exception as err:
        print(f"[CAMP MANAGER] Plantation error on {camp_id}: {err}", flush=True)


async def handle_env_telemetry(raw, state):
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            state["season"] = data.get("season", state["season"])
            state["date"] = data.get("date", state.get("date"))
            state["temperature"] = data.get("temperature", state.get("temperature", 20))
            state["weather"] = data.get("weather", state.get("weather", "Sunny"))

            if not state["occupied"]:
                state["empty_days"] += 1
            else:
                state["empty_days"] = 0
    except Exception:
        pass


async def handle_terrain_telemetry(mqtt, camp_id, raw, state):
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return

        state["moisture"] = data.get("soil_moisture", 28.0)
        state["oxygenation"] = data.get("oxygenation", 70.0)
        state["irrigation_active"] = data.get("irrigation_active", False)
        state["soil_type"] = data.get("soil_type", state.get("soil_type", "Franco"))
        state["water_dispensed_mm"] = data.get("water_dispensed_mm", 0.0)
        state["date"] = data.get("date", state.get("date"))

        target_min = state.get("min_moisture", 18.0) if state["occupied"] else 15.0
        target_max = target_min + 5.0

        if state["moisture"] < target_min and not state["irrigation_active"]:
            state["irrigation_active"] = True
            needed_water = round(max(2.0, target_max - state["moisture"]), 1)

            await mqtt.publish(f"camp/{camp_id}/terrain/cmd/irrigate", str(needed_water))
            notif = f"[{camp_id.upper()}] Sotto soglia ({state['moisture']:.1f}% < {target_min}%). Irrigato +{needed_water}%."
            print(f"[CAMP MANAGER] {notif}", flush=True)
            await mqtt.publish(NOTIFICATIONS_TOPIC, notif)

            logs = log_event("AUTO_IRRIGATE", f"[{camp_id}] Irrigato +{needed_water}%", state.get("date"), stats=state)
            await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))

        if state["oxygenation"] < 30.0:
            await mqtt.publish(f"camp/{camp_id}/terrain/cmd/reoxygenate", "trigger")
    except Exception as err:
        print(f"[CAMP MANAGER] Terrain telemetry error on {camp_id}: {err}", flush=True)


async def handle_dashboard_command(mqtt, camp_id, cmd, raw, state):
    clean_raw = raw.strip()
    parsed_json = None
    try:
        parsed_json = json.loads(clean_raw)
    except Exception:
        pass

    if cmd == "plant":
        seed_name = parsed_json.get("seed") if isinstance(parsed_json, dict) else clean_raw.lower()
        target = next((s for s in list_seeds if s["name"].lower() == str(seed_name).lower()), None)
        selected = target if target else {"name": seed_name}
        await plant_seed(mqtt, user_selected_seed=selected, camp_id=camp_id)
        state["empty_days"] = 0
        state["occupied"] = True

    elif cmd == "irrigate":
        target_min = state.get("min_moisture", 18.0) if state["occupied"] else 15.0
        target_max = target_min + 5.0
        needed_water = round(max(2.0, target_max - state["moisture"]), 1)
        state["irrigation_active"] = True
        await mqtt.publish(f"camp/{camp_id}/terrain/cmd/irrigate", str(needed_water))

    elif cmd == "clear":
        await clear_camp(mqtt, camp_id=camp_id)
        state["occupied"] = False
        state["seed_name"] = None
        state["harvest_pending"] = False

    elif cmd in ("skip", "skipdays", "skip_days"):
        days = 1
        if isinstance(parsed_json, dict):
            days = int(parsed_json.get("days", 1))
        elif clean_raw.isdigit():
            days = int(clean_raw)
        if not state["occupied"]:
            state["empty_days"] += days

    elif cmd == "reoxygenate":
        await mqtt.publish(f"camp/{camp_id}/terrain/cmd/reoxygenate", "trigger")

    elif cmd in ("reset", "restart"):
        state.update(create_default_state())


async def listen_telemetry(mqtt, camp_states):
    await mqtt.subscribe("camp/+/environment/telemetry")
    await mqtt.subscribe("camp/+/plantation/status")
    await mqtt.subscribe("camp/+/terrain/telemetry")
    await mqtt.subscribe("camp/+/camp_manager/cmd/#")

    async for msg in mqtt.messages:
        top = str(msg.topic)
        raw = msg.payload.decode("utf-8") if isinstance(msg.payload, bytes) else str(msg.payload)

        parts = top.split("/")
        if len(parts) >= 2 and parts[0] == "camp":
            camp_id = parts[1]
        else:
            continue

        if camp_id not in camp_states:
            camp_states[camp_id] = create_default_state()

        state = camp_states[camp_id]

        try:
            if "environment" in top:
                await handle_env_telemetry(raw, state)
            elif "plantation" in top:
                await process_plantation_status(mqtt, camp_id, msg.payload, state)
            elif "terrain" in top:
                await handle_terrain_telemetry(mqtt, camp_id, raw, state)
            elif "camp_manager/cmd/" in top:
                cmd = top.split("camp_manager/cmd/")[-1].lower()
                await handle_dashboard_command(mqtt, camp_id, cmd, raw, state)
        except Exception:
            pass


async def worker(camp_states):
    ssl_ctx = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_ctx,
        identifier="camp-manager-app",
    )
    async with client:
        print("[CAMP MANAGER] Multi-camp service online.", flush=True)

        tasks = [asyncio.create_task(listen_telemetry(client, camp_states))]
        for camp_id in KNOWN_CAMPS:
            tasks.append(asyncio.create_task(auto_plant_monitor_loop(client, camp_id, camp_states[camp_id])))

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                raise task.exception()


async def main():
    camp_states = {cid: create_default_state() for cid in KNOWN_CAMPS}

    while True:
        try:
            await worker(camp_states)
        except Exception as err:
            print(f"[CAMP MANAGER] Connection dropped ({err}). Reconnecting in 5s...", flush=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())