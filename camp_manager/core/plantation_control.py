import json
import aio_pika

from core.communication_par_man import AMQP_URL


async def plant_seed(mqtt_client=None, user_selected_seed=None, top_3_seeds=None):
    seed_to_plant = user_selected_seed
    if not seed_to_plant and top_3_seeds:
        seed_to_plant = top_3_seeds[0]

    if not seed_to_plant:
        print("[CAMP MANAGER] Error: No seed selected and no top seeds available.", flush=True)
        return False

    seed_name = seed_to_plant.get("name") if isinstance(seed_to_plant, dict) else str(seed_to_plant)

    conn = await aio_pika.connect_robust(AMQP_URL)
    async with conn:
        ch = await conn.channel()
        payload = json.dumps({"action": "PLANT", "seed": seed_to_plant})
        await ch.default_exchange.publish(
            aio_pika.Message(body=payload.encode()),
            routing_key="cmd_plantation"
        )

    print(f"[CAMP MANAGER] Dispatched PLANT command for: {seed_name}", flush=True)
    return True


async def clear_camp(mqtt_client=None):
    conn = await aio_pika.connect_robust(AMQP_URL)
    async with conn:
        ch = await conn.channel()
        payload = json.dumps({"action": "CLEAR"})
        await ch.default_exchange.publish(
            aio_pika.Message(body=payload.encode()),
            routing_key="cmd_plantation"
        )

    print("[CAMP MANAGER] Dispatched CLEAR command.", flush=True)
    return True


async def reset_camp(mqtt_client=None):
    conn = await aio_pika.connect_robust(AMQP_URL)
    async with conn:
        ch = await conn.channel()
        payload = json.dumps({"action": "RESET"})
        await ch.default_exchange.publish(
            aio_pika.Message(body=payload.encode()),
            routing_key="cmd_plantation"
        )

    print("[CAMP MANAGER] Dispatched RESET command.", flush=True)
    return True