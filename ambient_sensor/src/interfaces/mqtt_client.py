import asyncio

from interfaces.mqtt_utils import publish_json


async def dispatch_payload(handler, raw_payload):
    text = raw_payload.decode() if isinstance(raw_payload, bytes) else str(raw_payload)
    res = handler(text)
    if asyncio.iscoroutine(res):
        await res


async def publish_data(client, topic, data):
    # Lo stamping del timestamp ("ts") e' delegato a mqtt_utils.publish_json,
    # cosi' lo stesso identico codice/formato e' usato da tutti i servizi
    # (ambient, terrain, plantation, camp_manager) invece di essere
    # reimplementato qui.
    await publish_json(client, topic, data, qos=1)


async def listen_commands(client, handlers):
    if not handlers:
        return

    for target_topic in handlers:
        await client.subscribe(target_topic)

    async for msg in client.messages:
        t_name = str(msg.topic)
        if t_name in handlers:
            await dispatch_payload(handlers[t_name], msg.payload)