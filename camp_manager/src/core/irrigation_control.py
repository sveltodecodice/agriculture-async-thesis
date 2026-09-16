import logging
import aiomqtt
from common.constants import TOPIC_IRRIGATOR_IRRIGATE, TOPIC_IRRIGATOR_REOXYGENATE
from utils.mqtt_utils import publish_json

logger = logging.getLogger(__name__)


async def request_irrigation(
    mqtt_client: aiomqtt.Client, camp_id: str, amount: float
) -> None:
    """Publish an MQTT command to request irrigation for a target field.

    Args:
        mqtt_client (aiomqtt.Client): Active MQTT client connection.
        camp_id (str): Unique identifier of the field camp.
        amount (float): Required water amount percentage increase.
    """
    topic = TOPIC_IRRIGATOR_IRRIGATE.format(camp_id=camp_id)
    payload = {"amount": amount}
    await publish_json(mqtt_client, topic, payload, qos=1)
    logger.info("Irrigation requested | field=%s | amount=%.1f", camp_id, amount)


async def request_reoxygenation(mqtt_client: aiomqtt.Client, camp_id: str) -> None:
    """Publish an MQTT command to trigger soil reoxygenation.

    Args:
        mqtt_client (aiomqtt.Client): Active MQTT client connection.
        camp_id (str): Unique identifier of the target field camp.
    """
    topic = TOPIC_IRRIGATOR_REOXYGENATE.format(camp_id=camp_id)
    await mqtt_client.publish(topic, "trigger", qos=1)
    logger.info("Reoxygenation requested | field=%s", camp_id)
