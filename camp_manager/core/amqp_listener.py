import json
import aio_pika

from core.communication_par_man import (
    ACTIVITY_LOGS_TOPIC,
    HARVEST_DEPOSIT_TOPIC,
    NOTIFICATIONS_TOPIC,
)
from core.harvest_deposit import FILE_PATH
from core.irrigation_control import force_irrigation
from core.logger import clear_logs, log_event
from core.plantation_control import clear_camp, plant_seed
from core.seeds import list_seeds


async def handle_system_reset(mqtt, state):
    try:
        with open(FILE_PATH, "w") as f:
            json.dump([], f)

        state.update({
            "occupied": False,
            "empty_days": 0,
            "moisture": 60.0,
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
        })

        clear_logs()
        await clear_camp(mqtt)
        await mqtt.publish(HARVEST_DEPOSIT_TOPIC, "Harvest Deposit: Empty")
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps([]))
        await mqtt.publish("environment/cmd/reset", "01/01/2026")
        await mqtt.publish("terrain/cmd/reset", "trigger")
        await mqtt.publish("plantation/cmd/reset", "trigger")
        await mqtt.publish(NOTIFICATIONS_TOPIC, "System reset complete.")
        print("Full system reset complete.")
    except Exception as err:
        print(f"Reset failed: {err}")


async def handle_command(data, state, mqtt):
    act = str(data.get("action", "")).upper()

    if act in ("RESET", "RESTART"):
        await handle_system_reset(mqtt, state)

    elif act == "PLANT":
        seed_input = str(data.get("seed", "")).lower()
        target = next((s for s in list_seeds if s["name"].lower() == seed_input), None)
        if target:
            await plant_seed(mqtt, user_selected_seed=target)
            state["empty_days"] = 0
            state["occupied"] = True
            state["harvest_pending"] = False
            logs = log_event("PLANTED", f"Planted {target['name']}", state.get("date"), stats=state)
            await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))

    elif act == "CLEAR":
        await clear_camp(mqtt)
        state["occupied"] = False
        state["seed_name"] = None
        state["harvest_pending"] = False
        state["empty_days"] = 0
        logs = log_event("CLEARED", "Field cleared", state.get("date"), stats=state)
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))

    elif act == "IRRIGATE":
        await force_irrigation(mqtt, state["moisture"])
        logs = log_event("IRRIGATED", "Field manually irrigated", state.get("date"), stats=state)
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))

    elif act == "REOXYGENATE":
        await mqtt.publish("terrain/cmd/reoxygenate", "trigger")
        await mqtt.publish(NOTIFICATIONS_TOPIC, "Soil manually reoxygenated.")

    elif act == "SKIP":
        days = int(data.get("days", 1))
        await force_skip_days(mqtt, days, state)
        if not state["occupied"]:
            state["empty_days"] += days


async def process_message(msg, state, mqtt):
    async with msg.process(requeue=False):
        raw = msg.body.decode().strip()
        data = json.loads(raw) if raw.startswith("{") else {"action": raw}
        await handle_command(data, state, mqtt)


async def consume_amqp_commands(state, mqtt):
    conn = await aio_pika.connect_robust(AMQP_URL)
    ch = await conn.channel()
    await ch.set_qos(prefetch_count=1)

    dlx = await ch.declare_exchange("dlx_events", aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await ch.declare_queue("dlq_camp_manager_failures", durable=True)
    await dlq.bind(dlx, routing_key="camp_manager_cmd_failed")

    queue = await ch.declare_queue(
        "cmd_camp_manager",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "dlx_events",
            "x-dead-letter-routing-key": "camp_manager_cmd_failed",
        },
    )

    print("Listening for camp manager commands on AMQP...")
    async for msg in queue:
        await process_message(msg, state, mqtt)