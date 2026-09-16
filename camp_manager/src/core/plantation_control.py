import logging
import aiomqtt
from common.constants import (
    TOPIC_HARVESTER_HARVEST,
    TOPIC_PLANTATION_CLEARED,
    TOPIC_SEEDER_PLANT,
)
from utils.mqtt_utils import publish_json

logger = logging.getLogger(__name__)


async def request_seeding(
    mqtt_client: aiomqtt.Client, camp_id: str, seed: dict
) -> None:
    """Send a seeding command to the automated seeder actuator.

    Args:
        mqtt_client (aiomqtt.Client): Connected MQTT client instance.
        camp_id (str): Target field camp identifier.
        seed (dict): Dictionary with crop details to be planted.
    """
    topic = TOPIC_SEEDER_PLANT.format(camp_id=camp_id)
    await publish_json(mqtt_client, topic, seed, qos=1)
    logger.info("Seeding requested | field=%s | seed=%s", camp_id, seed.get("name"))


async def request_harvest(
    mqtt_client: aiomqtt.Client, camp_id: str, seed_name: str, harvest_date: str
) -> None:
    """Send a harvest command to the harvester actuator.

    Args:
        mqtt_client (aiomqtt.Client): Connected MQTT client instance.
        camp_id (str): Field camp identifier where crop is mature.
        seed_name (str): Name of the crop being harvested.
        harvest_date (str): Date string of when harvesting is executed.
    """
    topic = TOPIC_HARVESTER_HARVEST.format(camp_id=camp_id)
    payload = {"seed": seed_name, "date": harvest_date}
    await publish_json(mqtt_client, topic, payload, qos=1)
    logger.info("Harvest requested | field=%s | seed=%s", camp_id, seed_name)


async def publish_field_cleared_event(
    mqtt_client: aiomqtt.Client, camp_id: str, reason: str
) -> None:
    """Notify the system that a field has been cleared of crops.

    Args:
        mqtt_client (aiomqtt.Client): Connected MQTT client instance.
        camp_id (str): Field camp identifier.
        reason (str): Reason for clearing (e.g., 'dashboard' manual clear).
    """
    topic = TOPIC_PLANTATION_CLEARED.format(camp_id=camp_id)
    payload = {"reason": reason}
    await publish_json(mqtt_client, topic, payload, qos=1)
    logger.info("Field cleared event | field=%s | reason=%s", camp_id, reason)
