import json

from communication_par_pla import SEED_ADVICE_TOPIC
from core.mqtt_utils import publish_json
from core.seed_matcher import find_top_3_seeds


async def process_and_send_advice(moisture, season, mqtt):
    top_seeds = find_top_3_seeds(moisture, season)

    payload = {
        "event": "SEED_RECOMMENDATION",
        "count": len(top_seeds),
        "seeds": top_seeds,
    }

    await publish_json(mqtt, SEED_ADVICE_TOPIC, payload)
    return payload