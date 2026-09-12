import json
import aio_pika

from core.communication_par_pla import PLANTATION_STATUS_TOPIC
from core.mqtt_utils import publish_json
from core.plant_conditions import clear_field, get_status, seed_planted


async def handle_command(data, state, dedup, mqtt):
    act = str(data.get("action", "")).upper()

    if act == "PLANT":
        seed = data.get("seed")
        if seed:
            seed_planted(seed)
            name = seed.get("name") if isinstance(seed, dict) else seed
            print(f"Successfully sowed: {name}")
            await publish_json(mqtt, PLANTATION_STATUS_TOPIC, get_status(state["moisture"]))

    elif act in ("HARVEST", "CLEAR"):
        clear_field()
        print("Field cleared.")
        await publish_json(mqtt, PLANTATION_STATUS_TOPIC, get_status(state["moisture"]))

    elif act == "RESET":
        clear_field()
        dedup.reset()
        print("Field status reset to vacant.")
        await publish_json(mqtt, PLANTATION_STATUS_TOPIC, get_status(state["moisture"]))


async def process_message(msg, state, dedup, mqtt):
    async with msg.process(requeue=False):
        raw = msg.body.decode().strip()
        data = json.loads(raw) if raw.startswith("{") else {"action": raw}
        await handle_command(data, state, dedup, mqtt)


async def consume_amqp_commands(state, dedup, mqtt):
    conn = await aio_pika.connect_robust(AMQP_URL)
    ch = await conn.channel()
    await ch.set_qos(prefetch_count=1)

    dlx = await ch.declare_exchange("dlx_events", aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await ch.declare_queue("dlq_plantation_failures", durable=True)
    await dlq.bind(dlx, routing_key="plantation_cmd_failed")

    queue = await ch.declare_queue(
        "cmd_plantation",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "dlx_events",
            "x-dead-letter-routing-key": "plantation_cmd_failed",
        },
    )

    print("Listening for plantation commands on AMQP...")
    async for msg in queue:
        await process_message(msg, state, dedup, mqtt)