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
    PLANTATION_STATUS_TOPIC,
    TELEMETRY_ENV_TOPIC,
    TELEMETRY_TERRAIN_TOPIC,
    TOP_SEEDS_TOPIC,
)
from core.harvest_deposit import FILE_PATH, get_harvest_history, save_harvest
from core.irrigation_control import auto_irrigate, force_irrigation
from core.logger import clear_logs, get_logs, log_event
from core.plantation_control import clear_camp, plant_seed
from core.seed_matcher import find_top_3_seeds
from core.seeds import list_seeds


async def auto_plant_monitor_loop(mqtt, state):
    while True:
        await asyncio.sleep(5)
        if state["occupied"] or state["empty_days"] < 3:
            continue

        season = state.get("season", "spring")
        top_seeds = find_top_3_seeds(state["moisture"], season)
        target = top_seeds[0] if top_seeds else list_seeds[0]

        log_msg = f"Field vacant for 3 days. Auto-planted {target['name']}."
        print(f"[CAMP MANAGER] {log_msg}", flush=True)
        await mqtt.publish(NOTIFICATIONS_TOPIC, log_msg)

        await plant_seed(mqtt, user_selected_seed=target)
        state["empty_days"] = 0
        state["occupied"] = True

        logs = log_event("AUTO_PLANT", f"Auto-planted {target['name']}", state.get("date"), stats=state)
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))


async def process_plantation_status(mqtt, payload_bytes, state):
    try:
        data = json.loads(payload_bytes.decode("utf-8"))
        detail = data.get("status_detail") or {}
        plant_name = detail.get("plant_name") if isinstance(detail, dict) else None

        if not data.get("camp_availability", False) or not plant_name or plant_name in ("None", "Unknown"):
            state["occupied"] = False
            state["seed_name"] = None
            state["harvest_pending"] = False
            return

        state["occupied"] = True
        state["empty_days"] = 0
        state["seed_name"] = plant_name
        state["time_left"] = detail.get("time_left", 0)
        state["min_moisture"] = detail.get("min_soilmoisture", 20.0)

        if not (state["occupied"] and state["time_left"] <= 0 and not state["harvest_pending"]):
            return

        state["harvest_pending"] = True
        log_msg = f"{state['seed_name']} growth complete! Auto-harvesting..."
        print(f"[CAMP MANAGER] {log_msg}", flush=True)
        await mqtt.publish(NOTIFICATIONS_TOPIC, log_msg)

        history = save_harvest(state["seed_name"], state.get("date"))
        await mqtt.publish(HARVEST_DEPOSIT_TOPIC, json.dumps(history))

        logs = log_event("AUTO_HARVEST", f"Harvested {state['seed_name']}", state.get("date"), stats=state)
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))

        await clear_camp(mqtt)
        state["occupied"] = False
        state["seed_name"] = None
    except Exception as err:
        print(f"[CAMP MANAGER] Plantation status error: {err}", flush=True)


async def handle_env_telemetry(raw, state):
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            state["season"] = data.get("season", state["season"])
            state["date"] = data.get("date", state.get("date"))
            state["temperature"] = data.get("temperature", state.get("temperature", 20))
            state["weather"] = data.get("weather", state.get("weather", "Sunny"))
            state["wind_kmh"] = data.get("wind_kmh", 10.0)
            state["radiation_wm2"] = data.get("radiation_wm2", 500.0)
            state["rain_mm"] = data.get("rain_mm", 0.0)
            state["humidity_air"] = data.get("humidity_air", 50.0)

            if not state["occupied"]:
                state["empty_days"] += 1
            else:
                state["empty_days"] = 0
    except Exception:
        pass


async def handle_terrain_telemetry(mqtt, raw, state):
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return

        state["moisture"] = data.get("soil_moisture", 50.0)
        state["oxygenation"] = data.get("oxygenation", 70.0)
        state["irrigation_active"] = data.get("irrigation_active", False)
        state["soil_type"] = data.get("soil_type", state.get("soil_type", "Loam"))
        state["water_dispensed_mm"] = data.get("water_dispensed_mm", 0.0)
        state["date"] = data.get("date", state.get("date"))

        if state["date"] != state["last_log_date"]:
            state["last_log_date"] = state["date"]
            logs = log_event("DAILY_SNAPSHOT", "Daily Farm Status", state["date"], stats=state)
            await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))

        top_seeds = find_top_3_seeds(state["moisture"], state.get("season", "spring"))
        top_names = [s["name"].capitalize() for s in top_seeds[:3]]
        await mqtt.publish(TOP_SEEDS_TOPIC, "Top 3 Seeds: " + ", ".join(top_names))

        target_min = state["min_moisture"] if state["occupied"] else 20.0

        if state["moisture"] <= max(target_min, 20.0) and not state["irrigation_active"]:
            await auto_irrigate(mqtt, current_moisture=state["moisture"], min_moisture=target_min)
            await mqtt.publish(NOTIFICATIONS_TOPIC, f"Auto-irrigating! Moisture at {state['moisture']}%.")
            logs = log_event("AUTO_IRRIGATE", "Triggered auto-irrigation", state.get("date"), stats=state)
            await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))

        if state["oxygenation"] < 30.0:
            await mqtt.publish("terrain/cmd/reoxygenate", "trigger")
            await mqtt.publish(NOTIFICATIONS_TOPIC, f"Auto-oxygenating! Level at {state['oxygenation']}%.")
            logs = log_event("AUTO_OXYGENATE", "Triggered auto-oxygenation", state.get("date"), stats=state)
            await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))
    except Exception:
        pass


async def handle_dashboard_command(mqtt, cmd, raw, state):
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
        await plant_seed(mqtt, user_selected_seed=selected)
        state["empty_days"] = 0
        state["occupied"] = True

    elif cmd == "irrigate":
        await force_irrigation(mqtt, state["moisture"])

    elif cmd == "clear":
        await clear_camp(mqtt)
        state["occupied"] = False
        state["seed_name"] = None
        state["harvest_pending"] = False

    elif cmd in ("skip", "skipdays", "skip_days"):
        days = 1
        if isinstance(parsed_json, dict):
            days = int(parsed_json.get("days", 1))
        elif clean_raw.isdigit():
            days = int(clean_raw)

        await mqtt.publish("environment/cmd/skip", str(days))
        if not state["occupied"]:
            state["empty_days"] += days

        print(f"[CAMP MANAGER] Dispatched SKIP command for {days} days.", flush=True)
        await mqtt.publish(NOTIFICATIONS_TOPIC, f"Skipped {days} days.")

    elif cmd == "reoxygenate":
        await mqtt.publish("terrain/cmd/reoxygenate", "trigger")
        await mqtt.publish(NOTIFICATIONS_TOPIC, "Soil manually reoxygenated.")

    elif cmd in ("set_soil_type", "soil_type"):
        soil_type = parsed_json.get("type") if isinstance(parsed_json, dict) else clean_raw
        await mqtt.publish("terrain/cmd/set_soil_type", str(soil_type))
        await mqtt.publish(NOTIFICATIONS_TOPIC, f"Soil type changed to {soil_type}.")

    elif cmd in ("reset", "restart"):
        with open(FILE_PATH, "w") as f:
            json.dump([], f)

        state.update({
            "occupied": False, "empty_days": 0, "moisture": 60.0, "oxygenation": 70.0,
            "temperature": 20, "weather": "Sunny", "irrigation_active": False,
            "season": "winter", "date": "01/01/2026", "last_log_date": None,
            "seed_name": None, "min_moisture": 20.0, "max_moisture": 80.0,
            "time_left": 0, "harvest_pending": False, "soil_type": "Loam",
            "water_dispensed_mm": 0.0,
        })

        clear_logs()
        await clear_camp(mqtt)
        await mqtt.publish(HARVEST_DEPOSIT_TOPIC, "Harvest Deposit: Empty")
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps([]))

        await mqtt.publish("environment/cmd/reset", "01/01/2026")
        await mqtt.publish("terrain/cmd/reset", "trigger")
        await mqtt.publish("plantation/cmd/reset", "trigger")

        await mqtt.publish(NOTIFICATIONS_TOPIC, "System reset complete.")
        print("[CAMP MANAGER] Full system reset complete.", flush=True)


async def listen_telemetry(mqtt, state):
    await mqtt.subscribe(TELEMETRY_ENV_TOPIC)
    await mqtt.subscribe(PLANTATION_STATUS_TOPIC)
    await mqtt.subscribe(TELEMETRY_TERRAIN_TOPIC)
    await mqtt.subscribe("camp_manager/cmd/#")

    history = get_harvest_history()
    history_payload = json.dumps(history) if history else "Harvest Deposit: Empty"
    await mqtt.publish(HARVEST_DEPOSIT_TOPIC, history_payload)
    await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(get_logs()))

    async for msg in mqtt.messages:
        top = str(msg.topic)
        raw = msg.payload.decode("utf-8") if isinstance(msg.payload, bytes) else str(msg.payload)

        try:
            if top == TELEMETRY_ENV_TOPIC:
                await handle_env_telemetry(raw, state)
            elif top == PLANTATION_STATUS_TOPIC:
                await process_plantation_status(mqtt, msg.payload, state)
            elif top == TELEMETRY_TERRAIN_TOPIC:
                await handle_terrain_telemetry(mqtt, raw, state)
            elif top.startswith("camp_manager/cmd/"):
                cmd = top.replace("camp_manager/cmd/", "").lower()
                await handle_dashboard_command(mqtt, cmd, raw, state)
        except Exception:
            pass


async def worker(state):
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
        print("[CAMP MANAGER] Service online. Starting tasks...", flush=True)

        t1 = asyncio.create_task(listen_telemetry(client, state))
        t2 = asyncio.create_task(auto_plant_monitor_loop(client, state))

        done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                raise task.exception()


async def main():
    state = {
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
        "soil_type": "Loam",
        "water_dispensed_mm": 0.0,
        "wind_kmh": 10.0,
        "radiation_wm2": 500.0,
        "rain_mm": 0.0,
        "humidity_air": 50.0,
    }

    while True:
        try:
            await worker(state)
        except Exception as err:
            print(f"[CAMP MANAGER] Connection dropped ({err}). Reconnecting in 5s...", flush=True)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())