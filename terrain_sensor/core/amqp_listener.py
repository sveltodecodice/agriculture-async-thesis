import json
import aio_pika

from core.communication_par_ter import AMQP_URL
from core.terrain_condition import create_terrain_state


async def handle_command(action, state, dedup):
    act = str(action).upper()
    if act in ("IRRIGATE", "IRRIGATION"):
        state["irrigation_active"] = True
        print("Irrigation requested. Pump active for next tick.")
    elif act in ("REOXYGENATE", "OXYGEN"):
        state["oxygenation"] = 100.0
        print("Soil reoxygenated to 100.0%.")
    elif act in ("RESET", "RESTART"):
        fresh = create_terrain_state(initial_moisture=30.0, initial_oxygen=70.0)
        state.clear()
        state.update(fresh)
        dedup.reset()
        print("Terrain sensor state reset back to initial 30.0% baseline.")


async def process_message(msg, state, dedup):
    async with msg.process(requeue=False):
        raw = msg.body.decode().strip()
        data = json.loads(raw) if raw.startswith("{") else {"action": raw}
        await handle_command(data.get("action", ""), state, dedup)


async def consume_amqp_commands(state, dedup):
    conn = await aio_pika.connect_robust(AMQP_URL)
    ch = await conn.channel()
    await ch.set_qos(prefetch_count=1)

    dlx = await ch.declare_exchange("dlx_events", aio_pika.ExchangeType.DIRECT, durable=True)
    dlq = await ch.declare_queue("dlq_terrain_failures", durable=True)
    await dlq.bind(dlx, routing_key="terrain_cmd_failed")

    queue = await ch.declare_queue(
        "cmd_terrain",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "dlx_events",
            "x-dead-letter-routing-key": "terrain_cmd_failed",
        },
    )

    print("Listening for terrain commands on AMQP...")
    async for msg in queue:
        await process_message(msg, state, dedup)