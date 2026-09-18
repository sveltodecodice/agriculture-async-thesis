import logging
import uuid

import aiomqtt

from common.constants import (
    TOPIC_IRRIGATOR_IRRIGATE,
    TOPIC_IRRIGATOR_REOXYGENATE,
)
from utils.mqtt_utils import publish_json

logger = logging.getLogger(__name__)


def new_request_id() -> str:
    """Create a compact operation correlation ID."""
    return uuid.uuid4().hex[:12]


async def request_irrigation(
    mqtt_client: aiomqtt.Client,
    camp_id: str,
    amount: float,
    request_id: str | None = None,
) -> str:
    """Request irrigation and return the correlation ID."""
    operation_id = request_id or new_request_id()
    topic = TOPIC_IRRIGATOR_IRRIGATE.format(camp_id=camp_id)
    payload = {
        "request_id": operation_id,
        "amount": amount,
    }
    await publish_json(mqtt_client, topic, payload, qos=1)
    logger.info(
        "Irrigation requested | field=%s | request=%s | amount=%.1f",
        camp_id,
        operation_id,
        amount,
    )
    return operation_id


async def request_reoxygenation(
    mqtt_client: aiomqtt.Client,
    camp_id: str,
    request_id: str | None = None,
) -> str:
    """Request reoxygenation and return the correlation ID."""
    operation_id = request_id or new_request_id()
    topic = TOPIC_IRRIGATOR_REOXYGENATE.format(camp_id=camp_id)
    payload = {"request_id": operation_id}
    await publish_json(mqtt_client, topic, payload, qos=1)
    logger.info(
        "Reoxygenation requested | field=%s | request=%s",
        camp_id,
        operation_id,
    )
    return operation_id
