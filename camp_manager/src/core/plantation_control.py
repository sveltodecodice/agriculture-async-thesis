import json
import logging

logger = logging.getLogger(__name__)


async def plant_seed(mqtt, user_selected_seed, camp_id: str = "campo_1"):
    if isinstance(user_selected_seed, str):
        payload = json.dumps({"name": user_selected_seed.strip()})
    else:
        payload = json.dumps(user_selected_seed)

    topic = f"camp/{camp_id}/plantation/cmd/plant"
    await mqtt.publish(topic, payload)
    logger.info(
        f"[{camp_id.upper()}] Dispatched PLANT command for: {user_selected_seed.get('name') if isinstance(user_selected_seed, dict) else user_selected_seed}",
    )


async def clear_camp(mqtt, camp_id: str = "campo_1"):
    topic = f"camp/{camp_id}/plantation/cmd/clear"
    await mqtt.publish(topic, "trigger")
    logger.info(f"[{camp_id.upper()}] Dispatched CLEAR command.")
