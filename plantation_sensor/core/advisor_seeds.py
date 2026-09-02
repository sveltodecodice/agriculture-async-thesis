import json
from camp_manager.core.seed_matcher import find_top_3_seeds

async def process_and_send_advice(moisture: float, season: str, mqtt_client) -> dict:
    top_seeds = find_top_3_seeds(moisture, season)
    
    payload = {
        "event": "SEED_RECOMMENDATION",
        "count": len(top_seeds),
        "seeds": top_seeds
    }

    await mqtt_client.publish(
        topic="camp_manager/seed_advice",
        payload=json.dumps(payload)
    )
    
    return payload