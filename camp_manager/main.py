import asyncio
import json
import ssl
import aio_pika
import aiomqtt

from core.amqp_listener import consume_amqp_commands
from core.communication_par_man import (
    ACTIVITY_LOGS_TOPIC,
    AMQP_URL,
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


async def send_amqp_command(routing_key: str, data: dict):
    ssl_ctx = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    conn = await aio_pika.connect_robust(AMQP_URL, ssl_context=ssl_ctx)
    async with conn:
        ch = await conn.channel()
        await ch.default_exchange.publish(
            aio_pika.Message(body=json.dumps(data).encode()),
            routing_key=routing_key
        )


async def auto_plant_monitor_loop(mqtt, state):
    while True:
        await asyncio.sleep(5)
        if state["occupied"] or state["empty_days"] < 3:
            continue

        season = state.get("season", "spring")
        top_seeds = find_top_3_seeds(state["moisture"], season)
        target = top_seeds[0] if top_seeds else list_seeds[0]

        log_msg = f"Field vacant for 3 days. Auto-planted {target['name']}."
        print(log_msg)
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

        if not data.get("camp_availability", False) or not plant_name or plant_name == "None":
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
        print(log_msg)
        await mqtt.publish(NOTIFICATIONS_TOPIC, log_msg)

        history = save_harvest(state["seed_name"], state.get("date"))
        await mqtt.publish(HARVEST_DEPOSIT_TOPIC, json.dumps(history))

        logs = log_event("AUTO_HARVEST", f"Harvested {state['seed_name']}", state.get("date"), stats=state)
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))

        await clear_camp(mqtt)
        state["occupied"] = False
        state["seed_name"] = None
    except Exception as err:
        print(f"Plantation status error: {err}")


async def handle_env_telemetry(raw, state):
    data = json.loads(raw)
    state["season"] = data.get("season", state["season"])
    state["date"] = data.get("date", state.get("date"))
    state["temperature"] = data.get("temperature", state.get("temperature", 20))
    state["weather"] = data.get("weather", state.get("weather", "Sunny"))

    if not state["occupied"]:
        state["empty_days"] += 1
    else:
        state["empty_days"] = 0


async def handle_terrain_telemetry(mqtt, raw, state):
    data = json.loads(raw)
    state["moisture"] = data.get("soil_moisture", 50.0)
    state["oxygenation"] = data.get("oxygenation", 70.0)
    state["irrigation_active"] = data.get("irrigation_active", False)
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
        await send_amqp_command("cmd_terrain", {"action": "REOXYGENATE"})
        await mqtt.publish(NOTIFICATIONS_TOPIC, f"Auto-oxygenating! Level at {state['oxygenation']}%.")
        logs = log_event("AUTO_OXYGENATE", "Triggered auto-oxygenation", state.get("date"), stats=state)
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))


async def handle_dashboard_command(mqtt, cmd, raw, state):
    if cmd == "plant":
        seed_name = raw.strip().lower()
        target = next((s for s in list_seeds if s["name"].lower() == seed_name), None)
        selected = target if target else {"name": raw.strip()}
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

    elif cmd == "skip":
        try:
            days = int(raw.strip())
        except ValueError:
            try:
                days = int(json.loads(raw).get("days", 1))
            except Exception:
                days = 1

        await send_amqp_command("cmd_environment", {"action": "SKIP", "days": days})
        if not state["occupied"]:
            state["empty_days"] += days

    elif cmd == "reoxygenate":
        await send_amqp_command("cmd_terrain", {"action": "REOXYGENATE"})
        await mqtt.publish(NOTIFICATIONS_TOPIC, "Soil manually reoxygenated.")

    elif cmd in ("reset", "restart"):
        with open(FILE_PATH, "w") as f:
            json.dump([], f)

        state.update({
            "occupied": False, "empty_days": 0, "moisture": 60.0, "oxygenation": 70.0,
            "temperature": 20, "weather": "Sunny", "irrigation_active": False,
            "season": "winter", "date": "01/01/2026", "last_log_date": None,
            "seed_name": None, "min_moisture": 20.0, "max_moisture": 80.0,
            "time_left": 0, "harvest_pending": False,
        })

        clear_logs()
        await clear_camp(mqtt)
        await mqtt.publish(HARVEST_DEPOSIT_TOPIC, "Harvest Deposit: Empty")
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps([]))

        for q in ("cmd_environment", "cmd_terrain", "cmd_plantation"):
            await send_amqp_command(q, {"action": "RESET"})

        await mqtt.publish(NOTIFICATIONS_TOPIC, "System reset complete.")
        print("Full system reset complete.")


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


async def worker(state, dedup=None):
    ssl_ctx = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_ctx
    )
    async with client:
        print("Service online. Starting tasks...")

        t1 = asyncio.create_task(listen_telemetry(client, state))
        t2 = asyncio.create_task(auto_plant_monitor_loop(client, state))
        t3 = asyncio.create_task(consume_amqp_commands(state, client))

        done, pending = await asyncio.wait([t1, t2, t3], return_when=asyncio.FIRST_EXCEPTION)

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
    }

    while True:
        try:
            await worker(state)
        except Exception as err:
            print(f"Camp manager connection dropped ({err}). Reconnecting in 5s...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())