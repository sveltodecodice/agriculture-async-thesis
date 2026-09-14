import asyncio
import copy
import json
import logging
import os
import ssl
import time
from datetime import datetime, timezone
from typing import Any, Dict

import aiomqtt
from common.constants import DEFAULT_STATE, KNOWN_CAMPS, SEED_TARGETS
from common.parameters import (
    ACTIVITY_LOGS_TOPIC,
    CAMP_MANAGER_STATUS_TOPIC,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    NOTIFICATIONS_TOPIC,
)
from common.seeds import SEEDS_LST
from core.daily_report_producer import add_to_daily_report
from core.seed_matcher import find_top_3_seeds
from utils.logger_utils import LoggingUtils

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)


def configured_camps() -> list[str]:
    """Return camp IDs managed by this service.

    CAMP_IDS can be supplied as a comma-separated environment variable.
    Falls back to KNOWN_CAMPS for backward compatibility.
    """
    raw = os.getenv("CAMP_IDS", "").strip()
    if raw:
        return [camp.strip() for camp in raw.split(",") if camp.strip()]
    return list(KNOWN_CAMPS)


CONFIGURED_CAMPS = configured_camps()


def utc_now() -> str:
    """Returns the current UTC timestamp formatted in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_sensor_heartbeat(
    state: Dict[str, Any], sensor_type: str, payload_data: Dict[str, Any]
) -> None:
    """Records the arrival timestamp and latency of incoming sensor telemetry.

    Args:
        state (Dict[str, Any]): Target camp state dictionary.
        sensor_type (str): Identifier of the sensor ('environment', 'terrain', or 'plantation').
        payload_data (Dict[str, Any]): Decoded JSON payload from the sensor.
    """
    now = time.time()
    payload_ts = payload_data.get("ts") if isinstance(payload_data, dict) else None
    latency_ms = 0.0

    if payload_ts is not None:
        try:
            latency_ms = max(0.0, round((now - float(payload_ts)) * 1000.0, 2))
        except (TypeError, ValueError):
            latency_ms = 0.0

    if "sensor_health" not in state:
        state["sensor_health"] = {}

    state["sensor_health"][sensor_type] = {
        "last_seen": now,
        "latency_ms": latency_ms,
    }


async def manager_heartbeat_loop(
    mqtt: aiomqtt.Client, camp_states: Dict[str, Dict[str, Any]]
) -> None:
    """Publishes periodic service presence heartbeat messages for camp manager."""
    while True:
        payload = {
            "service": "camp_manager",
            "status": "online",
            "observed_at": utc_now(),
            "camps": sorted(camp_states.keys()),
        }
        await mqtt.publish(
            CAMP_MANAGER_STATUS_TOPIC,
            json.dumps(payload),
            qos=1,
            retain=True,
        )
        await asyncio.sleep(5)


async def system_health_monitor_loop(
    mqtt: aiomqtt.Client, camp_states: Dict[str, Dict[str, Any]]
) -> None:
    """Periodically evaluates sensor heartbeats and publishes system health status."""
    offline_threshold_seconds = 30.0

    while True:
        await asyncio.sleep(5)
        now = time.time()

        for camp_id, state in camp_states.items():
            sensor_health = state.get("sensor_health", {})
            sensors_status = {}
            all_online = True

            for sensor_name in ("environment", "terrain", "plantation"):
                info = sensor_health.get(sensor_name, {})
                last_seen = info.get("last_seen", 0.0)

                if last_seen > 0:
                    seconds_ago = round(now - last_seen, 1)
                    is_online = seconds_ago <= offline_threshold_seconds
                else:
                    seconds_ago = None
                    is_online = False

                if not is_online:
                    all_online = False

                sensors_status[sensor_name] = {
                    "status": "ONLINE" if is_online else "OFFLINE",
                    "last_seen_seconds_ago": seconds_ago,
                    "latency_ms": info.get("latency_ms", 0.0),
                }

            system_payload = {
                "camp_id": camp_id,
                "mqtt_connected": True,
                "overall_health": "HEALTHY" if all_online else "DEGRADED",
                "sensors": sensors_status,
                "updated_at": utc_now(),
            }

            topic = f"camp/{camp_id}/system/status"
            await mqtt.publish(topic, json.dumps(system_payload))


async def request_seeding(mqtt: aiomqtt.Client, camp_id: str, seed: dict) -> None:
    """Send a planting command to the seeder actuator."""
    topic = f"camp/{camp_id}/seeder/cmd/plant"
    await mqtt.publish(topic, json.dumps(seed), qos=1)
    logger.info(
        "Seeding requested | field=%s | seed=%s",
        camp_id,
        seed.get("name"),
    )


async def request_harvest(
    mqtt: aiomqtt.Client, camp_id: str, seed_name: str, harvest_date: str
) -> None:
    """Send a harvest command to the harvester actuator."""
    topic = f"camp/{camp_id}/harvester/cmd/harvest"
    payload = {
        "seed": seed_name,
        "date": harvest_date,
    }
    await mqtt.publish(topic, json.dumps(payload), qos=1)
    logger.info(
        "Harvest requested | field=%s | seed=%s",
        camp_id,
        seed_name,
    )


async def request_irrigation(
    mqtt: aiomqtt.Client, camp_id: str, amount: float
) -> None:
    """Send an irrigation command to the irrigator actuator."""
    topic = f"camp/{camp_id}/irrigator/cmd/irrigate"
    payload = {"amount": amount}
    await mqtt.publish(topic, json.dumps(payload), qos=1)
    logger.info(
        "Irrigation requested | field=%s | amount=%.1f",
        camp_id,
        amount,
    )


async def request_reoxygenation(mqtt: aiomqtt.Client, camp_id: str) -> None:
    """Send a soil reoxygenation command to the irrigator actuator."""
    topic = f"camp/{camp_id}/irrigator/cmd/reoxygenate"
    await mqtt.publish(topic, "trigger", qos=1)
    logger.info("Reoxygenation requested | field=%s", camp_id)


async def publish_field_cleared_event(
    mqtt: aiomqtt.Client, camp_id: str, reason: str
) -> None:
    """Publish the fact that the simulated field has been cleared."""
    topic = f"camp/{camp_id}/plantation/event/cleared"
    payload = {"reason": reason}
    await mqtt.publish(topic, json.dumps(payload), qos=1)
    logger.info("Field cleared event | field=%s | reason=%s", camp_id, reason)


async def auto_plant_monitor_loop(
    mqtt: aiomqtt.Client, camp_id: str, state: Dict[str, Any]
) -> None:
    """Monitors empty camp fields and triggers automatic seed planting."""
    while True:
        await asyncio.sleep(4)
        if (
            state["occupied"]
            or state.get("seeding_pending", False)
            or state.get("empty_days", 0) < 3
        ):
            continue

        season = state.get("season", "spring")
        top_seeds = find_top_3_seeds(state["moisture"], season)
        target = top_seeds[0] if top_seeds else SEEDS_LST[0]

        msg = f"[{camp_id.upper()}] Campo libero. Richiesta autosemina: {target['name'].capitalize()}."

        logger.info(msg)
        await mqtt.publish(NOTIFICATIONS_TOPIC, msg)

        await request_seeding(mqtt, camp_id, target)
        state["seeding_pending"] = True
        state["empty_days"] = 0

        logs = add_to_daily_report(
            "AUTO_PLANT",
            f"[{camp_id}] Richiesta autosemina {target['name']}",
            state.get("date"),
            stats=state,
        )
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))


async def process_plantation_status(
    mqtt: aiomqtt.Client, camp_id: str, payload_bytes: bytes, state: Dict[str, Any]
) -> None:
    """Processes plantation status telemetry, growth progress, and auto-harvesting."""
    try:
        data = json.loads(payload_bytes.decode("utf-8"))
        record_sensor_heartbeat(state, "plantation", data)

        detail = data.get("status_detail") or {}
        plant_name = detail.get("plant_name") if isinstance(detail, dict) else None

        if (
            not data.get("camp_availability", False)
            or not plant_name
            or plant_name in ("None", "Unknown")
        ):
            state["occupied"] = False
            state["seed_name"] = None
            state["harvest_pending"] = False
            state["min_moisture"] = 18.0
            state["growth_percentage"] = 0.0
            state["growth_stage"] = "EMPTY"
            state["health"] = "FIELD IS EMPTY"
            return

        state["occupied"] = True
        state["seeding_pending"] = False
        state["empty_days"] = 0
        state["seed_name"] = plant_name
        state["time_left"] = detail.get("time_left", 0)
        state["growth_percentage"] = detail.get("growth_percentage", 0.0)
        state["growth_stage"] = detail.get("growth_stage", "EMPTY")
        state["health"] = detail.get("health", "HEALTHY")

        clean_name = str(plant_name).lower()
        state["min_moisture"] = detail.get(
            "min_soilmoisture", SEED_TARGETS.get(clean_name, 18.0)
        )

        if not (
            state["occupied"]
            and state["time_left"] <= 0
            and not state["harvest_pending"]
        ):
            return

        state["harvest_pending"] = True
        log_msg = f"[{camp_id.upper()}] {state['seed_name']} maturazione completata! Auto-raccolto in corso..."
        logger.info("%s", log_msg)
        await mqtt.publish(NOTIFICATIONS_TOPIC, log_msg)

        await request_harvest(
            mqtt,
            camp_id,
            state["seed_name"],
            state.get("date"),
        )

        logs = add_to_daily_report(
            "AUTO_HARVEST",
            f"[{camp_id}] Richiesto raccolto {state['seed_name']}",
            state.get("date"),
            stats=state,
        )
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))
    except Exception as err:
        logger.error("Plantation error on %s: %s", camp_id, err)


async def handle_env_telemetry(raw_data: str, state: Dict[str, Any]) -> None:
    """Updates camp state with environment telemetry readings."""
    try:
        data = json.loads(raw_data)
        if isinstance(data, dict):
            record_sensor_heartbeat(state, "environment", data)
            new_date = data.get("date")
            old_date = state.get("date")

            state["season"] = data.get("season", state["season"])
            state["temperature"] = data.get("temperature", state.get("temperature", 20))
            state["weather"] = data.get("weather", state.get("weather", "Sunny"))

            if new_date and new_date != old_date:
                state["date"] = new_date
                if not state["occupied"]:
                    state["empty_days"] += 1
                else:
                    state["empty_days"] = 0
            elif new_date:
                state["date"] = new_date
    except Exception as e:
        logger.error("Environment telemetry error: %s", e)


async def handle_terrain_telemetry(
    mqtt: aiomqtt.Client, camp_id: str, raw_data: str, state: Dict[str, Any]
) -> None:
    """Processes terrain soil moisture/oxygenation readings and handles auto-irrigation."""
    try:
        data = json.loads(raw_data)
        if not isinstance(data, dict):
            return

        record_sensor_heartbeat(state, "terrain", data)

        state["moisture"] = data.get("soil_moisture", 28.0)
        state["oxygenation"] = data.get("oxygenation", 70.0)
        state["irrigation_active"] = data.get("irrigation_active", False)
        state["soil_type"] = data.get("soil_type", state.get("soil_type", "Franco"))
        state["water_dispensed_mm"] = data.get("water_dispensed_mm", 0.0)
        state["date"] = data.get("date", state.get("date"))

        target_min = state.get("min_moisture", 18.0) if state["occupied"] else 15.0
        target_max = target_min + 5.0

        if state["moisture"] < target_min and not state["irrigation_active"]:
            state["irrigation_active"] = True
            needed_water = round(max(2.0, target_max - state["moisture"]), 1)

            await request_irrigation(mqtt, camp_id, needed_water)
            notif = f"[{camp_id.upper()}] Sotto soglia ({state['moisture']:.1f}% < {target_min}%). Richiesta irrigazione +{needed_water}%."
            logger.info("%s", notif)
            await mqtt.publish(NOTIFICATIONS_TOPIC, notif)

            logs = add_to_daily_report(
                "AUTO_IRRIGATE",
                f"[{camp_id}] Richiesta irrigazione +{needed_water}%",
                state.get("date"),
                stats=state,
            )
            await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))

        if state["oxygenation"] < 30.0:
            await request_reoxygenation(mqtt, camp_id)
    except Exception as err:
        logger.error("Terrain telemetry error on %s: %s", camp_id, err)


async def handle_dashboard_command(
    mqtt: aiomqtt.Client,
    camp_id: str,
    cmd: str,
    raw_data: str,
    state: Dict[str, Any],
) -> None:
    """Executes administrative dashboard commands for a target camp."""
    clean_raw_data = raw_data.strip()
    parsed_json = None
    try:
        parsed_json = json.loads(clean_raw_data)
    except Exception:
        pass

    if cmd == "plant":
        seed_name = (
            parsed_json.get("seed")
            if isinstance(parsed_json, dict)
            else clean_raw_data.lower()
        )
        target = next(
            (s for s in SEEDS_LST if s["name"].lower() == str(seed_name).lower()), None
        )
        selected = target if target else {"name": seed_name}
        await request_seeding(mqtt, camp_id, selected)
        state["seeding_pending"] = True
        state["empty_days"] = 0

    elif cmd == "irrigate":
        target_min = state.get("min_moisture", 18.0) if state["occupied"] else 15.0
        target_max = target_min + 5.0
        needed_water = round(max(2.0, target_max - state["moisture"]), 1)
        state["irrigation_active"] = True
        await request_irrigation(mqtt, camp_id, needed_water)

    elif cmd == "clear":
        await publish_field_cleared_event(mqtt, camp_id, reason="dashboard")
        state["occupied"] = False
        state["seeding_pending"] = False
        state["seed_name"] = None
        state["harvest_pending"] = False
        state["growth_percentage"] = 0.0
        state["growth_stage"] = "EMPTY"
        state["health"] = "FIELD IS EMPTY"

    elif cmd in ("skip", "skipdays", "skip_days"):
        days = 1
        if isinstance(parsed_json, dict):
            days = int(parsed_json.get("days", 1))
        elif clean_raw_data.isdigit():
            days = int(clean_raw_data)
        if not state["occupied"]:
            state["empty_days"] += days

    elif cmd == "reoxygenate":
        await request_reoxygenation(mqtt, camp_id)

    elif cmd in ("reset", "restart"):
        state.clear()
        state.update(copy.deepcopy(DEFAULT_STATE))


async def listen_telemetry(
    mqtt: aiomqtt.Client, camp_states: Dict[str, Dict[str, Any]]
) -> None:
    """Listens to all camp telemetry and command topics."""
    await mqtt.subscribe("camp/+/environment/telemetry")
    await mqtt.subscribe("camp/+/plantation/status")
    await mqtt.subscribe("camp/+/terrain/telemetry")
    await mqtt.subscribe("camp/+/camp_manager/cmd/#")

    async for message in mqtt.messages:
        topic = str(message.topic)
        raw_data = (
            message.payload.decode("utf-8")
            if isinstance(message.payload, bytes)
            else str(message.payload)
        )

        topic_parts = topic.split("/")
        if len(topic_parts) >= 2 and topic_parts[0] == "camp":
            camp_id = topic_parts[1]
        else:
            continue

        if camp_id not in camp_states:
            camp_states[camp_id] = copy.deepcopy(DEFAULT_STATE)

        state = camp_states[camp_id]

        try:
            if "environment" in topic:
                await handle_env_telemetry(raw_data, state)
            elif "plantation" in topic:
                await process_plantation_status(mqtt, camp_id, message.payload, state)
            elif "terrain" in topic:
                await handle_terrain_telemetry(mqtt, camp_id, raw_data, state)
            elif "camp_manager/cmd/" in topic:
                command = topic.split("camp_manager/cmd/")[-1].lower()
                await handle_dashboard_command(mqtt, camp_id, command, raw_data, state)
        except Exception:
            pass


async def worker(camp_states: Dict[str, Dict[str, Any]]) -> None:
    """Manages the MQTT client life cycle and supervises async worker loops."""
    ssl_context = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_context,
        identifier="camp-manager-app",
    )
    async with client:
        logger.info("Multi-camp service online.")

        tasks = [
            asyncio.create_task(listen_telemetry(client, camp_states)),
            asyncio.create_task(manager_heartbeat_loop(client, camp_states)),
            asyncio.create_task(system_health_monitor_loop(client, camp_states)),
        ]

        for camp_id in CONFIGURED_CAMPS:
            tasks.append(
                asyncio.create_task(
                    auto_plant_monitor_loop(client, camp_id, camp_states[camp_id])
                )
            )

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                raise task.exception()


async def main() -> None:
    """Service entry point initializing camp state maps and handling reconnects."""
    camp_states = {camp_id: copy.deepcopy(DEFAULT_STATE) for camp_id in CONFIGURED_CAMPS}

    while True:
        try:
            await worker(camp_states)
        except Exception as error:
            logger.error(
                "Connection dropped (%s). Reconnecting in 5s...",
                error,
                exc_info=True,
            )
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
