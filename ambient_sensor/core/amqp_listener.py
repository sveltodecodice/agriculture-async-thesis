import json
import aio_pika

from core.communication_par_amb import AMQP_URL, TELEMETRY_TOPIC
from core.manager import create_timer_state, update_environment
from core.mqtt_client import publish_data


async def handle_skip(payload, state, mqtt):
    raw_days = payload.get("days", payload.get("payload", 1))
    try:
        d_count = int(raw_days)
    except (ValueError, TypeError):
        d_count = 1

    for _ in range(max(1, d_count)):
        update_environment(state)
        await publish_data(mqtt, TELEMETRY_TOPIC, state)

    print(f"Skipped {d_count} day(s). Current date: {state['day']:02d}/{state['month']:02d}/{state['year']}")


async def handle_reset(state, mqtt):
    state.update(create_timer_state(d=1, m=1, y=2026))
    await publish_data(mqtt, TELEMETRY_TOPIC, state)
    print("Environment state reset to 01/01/2026")


async def process_message(msg, state, mqtt):
    async with msg.process(requeue=False):
        raw = msg.body.decode().strip()
        data = json.loads(raw) if raw.startswith("{") else {"action": "SKIP", "days": raw}
        act = str(data.get("action", "")).upper()

        if act in ("SKIP", "SKIP_DAY"):
            await handle_skip(data, state, mqtt)
        elif act in ("RESET", "RESTART"):
            await handle_reset(state, mqtt)


async def consume_amqp_commands(state, mqtt):
    conn = await aio_pika.connect_robust(AMQP_URL)
    ch = await conn.channel()
    await ch.set_qos(prefetch_count=1)

    dlx = await ch.declare_exchange("dlx_events", aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await ch.declare_queue("dlq_ambient_failures", durable=True)
    await dlq.bind(dlx, routing_key="ambient_cmd_failed")

    queue = await ch.declare_queue(
        "cmd_environment",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "dlx_events",
            "x-dead-letter-routing-key": "ambient_cmd_failed",
        },
    )

    print("Listening for environment commands...")
    async for msg in queue:
        await process_message(msg, state, mqtt)