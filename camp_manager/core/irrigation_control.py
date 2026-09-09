import json
import aio_pika

from core.communication_par_man import AMQP_URL


async def force_irrigation(mqtt_client=None, current_moisture: float = 0.0, irrigation_amount: float = 25.0):
    print(f"Publishing command to FORCE irrigate. (Current moisture: {current_moisture}%)", flush=True)
    conn = await aio_pika.connect_robust(AMQP_URL)
    async with conn:
        ch = await conn.channel()
        payload = json.dumps({"action": "IRRIGATE", "amount": irrigation_amount})
        await ch.default_exchange.publish(
            aio_pika.Message(body=payload.encode()),
            routing_key="cmd_terrain"
        )


async def auto_irrigate(mqtt_client, current_moisture: float, min_moisture: float = 20.0, irrigation_amount: float = 25.0):
    minimal_moisture = max(min_moisture, 20.0)
    if current_moisture <= minimal_moisture:
        print(f"Moisture level ({current_moisture}%) fell below safety minimum ({minimal_moisture}%). Auto-irrigating!", flush=True)
        await force_irrigation(mqtt_client, current_moisture, irrigation_amount)