import json
from camp_manager.core.seed_matcher import find_top_3_seeds


def build_advice_payload(candidates: list) -> dict:
    return {
        "event": "SEED_RECOMMENDATION",
        "count": len(candidates),
        "seeds": candidates
    }


async def process_and_send_advice(moisture: float, season: str, mqtt_client) -> dict:
    top_seeds = find_top_3_seeds(moisture, season)
    payload = build_advice_payload(top_seeds)

    await mqtt_client.publish(
        topic="camp_manager/seed_advice",
        payload=json.dumps(payload)
    )

    return payload