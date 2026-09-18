import asyncio
import copy
import json
import logging
import ssl
import time
from datetime import datetime, timezone
from typing import Any, Dict

import aiomqtt
from common.constants import DEFAULT_STATE, SEED_TARGETS, TOPIC_SYSTEM_STATUS
from common.parameters import (
    ACTIVITY_LOGS_TOPIC,
    CAMP_MANAGER_STATUS_TOPIC,
    MQTT_CA_CERT,
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
    MQTT_RECONNECT_SECONDS,
    MQTT_CLIENT_ID,
    CONFIGURED_CAMPS,
    SENSOR_OFFLINE_SECONDS,
    HEALTH_PUBLISH_INTERVAL_SECONDS,
    MANAGER_HEARTBEAT_INTERVAL_SECONDS,
    AUTO_SEED_EMPTY_DAYS,
    AUTO_SEED_CHECK_INTERVAL_SECONDS,
    EMPTY_FIELD_MIN_MOISTURE,
    IRRIGATION_TARGET_MARGIN,
    MIN_IRRIGATION_AMOUNT,
    OXYGENATION_THRESHOLD,
    NOTIFICATIONS_TOPIC,
)
from common.seeds import SEEDS_LST
from core.daily_report_producer import add_to_daily_report
from core.harvest_deposit import save_harvest
from core.irrigation_control import request_irrigation, request_reoxygenation
from core.plantation_control import (
    publish_field_cleared_event,
    request_harvest,
    request_seeding,
)
from core.seed_matcher import find_top_3_seeds
from utils.logger_utils import LoggingUtils
from utils.mqtt_utils import Deduper, publish_json

LoggingUtils.configure(console_level=logging.INFO)
logger = LoggingUtils.get_logger(__name__)




def utc_now() -> str:
    """Get the current UTC timestamp formatted as ISO-8601 string.

    Returns:
        str: ISO-formatted timestamp string.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_sensor_heartbeat(
    state: Dict[str, Any], sensor_type: str, payload_data: Dict[str, Any]
) -> None:
    """Track last seen timestamp and estimated latency for a given sensor module.

    Args:
        state (Dict[str, Any]): In-memory state dictionary for a specific camp.
        sensor_type (str): Type of sensor ('environment', 'terrain', or 'plantation').
        payload_data (Dict[str, Any]): Decoded payload dictionary containing timestamp.
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


def record_actuator_heartbeat(
    state: Dict[str, Any], actuator_type: str, payload_data: Dict[str, Any]
) -> None:
    """Track actuator heartbeat plus its current operation state."""
    now = time.time()
    payload_ts = payload_data.get("ts") if isinstance(payload_data, dict) else None
    latency_ms = 0.0

    if payload_ts is not None:
        try:
            latency_ms = max(0.0, round((now - float(payload_ts)) * 1000.0, 2))
        except (TypeError, ValueError):
            latency_ms = 0.0

    actuator_health = state.setdefault("actuator_health", {})
    actuator_health[actuator_type] = {
        "last_seen": now,
        "latency_ms": latency_ms,
        "operation": payload_data.get("operation", "unknown"),
        "status": payload_data.get("status", "unknown"),
        "active_request_id": payload_data.get("active_request_id"),
        "last_request_id": payload_data.get("last_request_id"),
        "last_action": payload_data.get("last_action"),
        "last_amount": payload_data.get("last_amount"),
        "last_completed_at": payload_data.get("last_completed_at"),
    }


async def manager_heartbeat_loop(
    mqtt: aiomqtt.Client, camp_states: Dict[str, Dict[str, Any]]
) -> None:
    """Periodically publish manager status to confirm service operation.

    Args:
        mqtt (aiomqtt.Client): Active MQTT connection client.
        camp_states (Dict[str, Dict[str, Any]]): Global state tracking dictionary.
    """
    while True:
        payload = {
            "service": "camp_manager",
            "status": "online",
            "observed_at": utc_now(),
            "camps": sorted(camp_states.keys()),
        }
        await publish_json(mqtt, CAMP_MANAGER_STATUS_TOPIC, payload, qos=1, retain=True)
        await asyncio.sleep(MANAGER_HEARTBEAT_INTERVAL_SECONDS)


async def system_health_monitor_loop(
    mqtt: aiomqtt.Client, camp_states: Dict[str, Dict[str, Any]]
) -> None:
    """Publish sensor health, Irrigator health and automation state."""
    offline_threshold_seconds = SENSOR_OFFLINE_SECONDS

    while True:
        await asyncio.sleep(HEALTH_PUBLISH_INTERVAL_SECONDS)
        now = time.time()

        for camp_id, state in list(camp_states.items()):
            sensors_status = {}
            all_online = True

            for sensor_name in ("environment", "terrain", "plantation"):
                info = state.get("sensor_health", {}).get(sensor_name, {})
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

            actuators_status = {}
            for actuator_name in ("irrigator",):
                info = state.get("actuator_health", {}).get(actuator_name, {})
                last_seen = info.get("last_seen", 0.0)

                if last_seen > 0:
                    seconds_ago = round(now - last_seen, 1)
                    is_online = seconds_ago <= offline_threshold_seconds
                else:
                    seconds_ago = None
                    is_online = False

                if not is_online:
                    all_online = False

                actuators_status[actuator_name] = {
                    "status": "ONLINE" if is_online else "OFFLINE",
                    "last_seen_seconds_ago": seconds_ago,
                    "latency_ms": info.get("latency_ms", 0.0),
                    "operation": info.get("operation", "unknown"),
                    "active_request_id": info.get("active_request_id"),
                    "last_request_id": info.get("last_request_id"),
                    "last_action": info.get("last_action"),
                    "last_amount": info.get("last_amount"),
                    "last_completed_at": info.get("last_completed_at"),
                }

            target_min = (
                state.get("min_moisture", 18.0)
                if state.get("occupied")
                else EMPTY_FIELD_MIN_MOISTURE
            )

            system_payload = {
                "camp_id": camp_id,
                "mqtt_connected": True,
                "overall_health": "HEALTHY" if all_online else "DEGRADED",
                "sensors": sensors_status,
                "actuators": actuators_status,
                "automation": {
                    "irrigation": {
                        "pending": state.get("irrigation_pending", False),
                        "request_id": state.get("irrigation_request_id"),
                        "target_min_pct": target_min,
                        "target_after_pct": target_min + IRRIGATION_TARGET_MARGIN,
                    },
                    "reoxygenation": {
                        "pending": state.get("reoxygenation_pending", False),
                        "request_id": state.get("reoxygenation_request_id"),
                        "threshold_pct": OXYGENATION_THRESHOLD,
                    },
                },
                "updated_at": utc_now(),
            }

            topic = TOPIC_SYSTEM_STATUS.format(camp_id=camp_id)
            await publish_json(mqtt, topic, system_payload)


async def auto_plant_monitor_loop(
    mqtt: aiomqtt.Client, camp_id: str, state: Dict[str, Any]
) -> None:
    """Check empty field status and trigger automatic planting after 3 empty days.

    Args:
        mqtt (aiomqtt.Client): Active MQTT client connection.
        camp_id (str): Identifier of the monitored field camp.
        state (Dict[str, Any]): Field state record dictionary.
    """
    while True:
        await asyncio.sleep(AUTO_SEED_CHECK_INTERVAL_SECONDS)
        if (
            state["occupied"]
            or state.get("seeding_pending", False)
            or state.get("empty_days", 0) < AUTO_SEED_EMPTY_DAYS
        ):
            continue

        season = state.get("season", "spring")
        soil_type = state.get("soil_type", "Franco")
        top_seeds = find_top_3_seeds(
            state["moisture"],
            season,
            soil_type,
        )
        target = top_seeds[0] if top_seeds else SEEDS_LST[0]

        msg = (
            f"[{camp_id.upper()}] Campo libero ({soil_type}). "
            f"Richiesta autosemina: {target['name'].capitalize()}."
        )
        logger.info(msg)
        await mqtt.publish(NOTIFICATIONS_TOPIC, msg)

        await request_seeding(mqtt, camp_id, target)
        state["seeding_pending"] = True
        state["empty_days"] = 0

        logs = add_to_daily_report(
            "AUTO_PLANT",
            f"[{camp_id}] Richiesta autosemina {target['name']} | Soil: {soil_type}",
            state.get("date"),
            stats=state,
        )
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))


async def process_plantation_status(
    mqtt: aiomqtt.Client, camp_id: str, payload_bytes: bytes, state: Dict[str, Any]
) -> None:
    """Process crop telemetry updates and trigger automated harvesting on maturity.

    Args:
        mqtt (aiomqtt.Client): Active MQTT connection client.
        camp_id (str): Field camp identifier.
        payload_bytes (bytes): Raw JSON message bytes received from MQTT topic.
        state (Dict[str, Any]): Camp state dictionary to update.
    """
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

        await request_harvest(mqtt, camp_id, state["seed_name"], state.get("date"))
        save_harvest(state["seed_name"], state.get("date"))

        logs = add_to_daily_report(
            "AUTO_HARVEST",
            f"[{camp_id}] Richiesto raccolto {state['seed_name']}",
            state.get("date"),
            stats=state,
        )
        await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))
    except Exception as err:
        logger.error("Plantation error on %s: %s", camp_id, err, exc_info=True)


async def handle_env_telemetry(raw_data: str, state: Dict[str, Any]) -> None:
    """Parse environmental weather telemetry and update local state variables.

    Args:
        raw_data (str): Unparsed JSON string received from environment sensor.
        state (Dict[str, Any]): Camp state dictionary to update.
    """
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
        logger.error("Environment telemetry error: %s", e, exc_info=True)


async def handle_terrain_telemetry(
    mqtt: aiomqtt.Client, camp_id: str, raw_data: str, state: Dict[str, Any]
) -> None:
    """Process observed terrain state and request actuator operations when needed."""
    try:
        data = json.loads(raw_data)
        if not isinstance(data, dict):
            return

        record_sensor_heartbeat(state, "terrain", data)

        state["moisture"] = data.get("soil_moisture", 28.0)
        state["oxygenation"] = data.get("oxygenation", 70.0)
        state["soil_type"] = data.get("soil_type", state.get("soil_type", "Franco"))
        state["water_dispensed_mm"] = data.get("water_dispensed_mm", 0.0)
        state["date"] = data.get("date", state.get("date"))

        # Confirmation comes from Terrain Sensor telemetry after it observes the
        # completed Irrigator event. This prevents "command sent" from being
        # treated as "physical state changed".
        last_irrigation_id = data.get("last_irrigation_id")
        if (
            state.get("irrigation_pending")
            and last_irrigation_id
            and last_irrigation_id == state.get("irrigation_request_id")
        ):
            logger.info(
                "Irrigation confirmed by Terrain Sensor | field=%s | request=%s",
                camp_id,
                last_irrigation_id,
            )
            state["irrigation_pending"] = False
            state["irrigation_request_id"] = None

        last_reoxygenation_id = data.get("last_reoxygenation_id")
        if (
            state.get("reoxygenation_pending")
            and last_reoxygenation_id
            and last_reoxygenation_id == state.get("reoxygenation_request_id")
        ):
            logger.info(
                "Reoxygenation confirmed by Terrain Sensor | field=%s | request=%s",
                camp_id,
                last_reoxygenation_id,
            )
            state["reoxygenation_pending"] = False
            state["reoxygenation_request_id"] = None

        target_min = state.get("min_moisture", 18.0) if state["occupied"] else EMPTY_FIELD_MIN_MOISTURE
        target_max = target_min + IRRIGATION_TARGET_MARGIN

        if state["moisture"] < target_min and not state.get("irrigation_pending"):
            needed_water = round(max(MIN_IRRIGATION_AMOUNT, target_max - state["moisture"]), 1)
            request_id = await request_irrigation(mqtt, camp_id, needed_water)
            state["irrigation_pending"] = True
            state["irrigation_request_id"] = request_id

            notif = (
                f"[{camp_id.upper()}] Sotto soglia "
                f"({state['moisture']:.1f}% < {target_min}%). "
                f"Richiesta irrigazione +{needed_water}%."
            )
            logger.info("%s", notif)
            await mqtt.publish(NOTIFICATIONS_TOPIC, notif)

            logs = add_to_daily_report(
                "AUTO_IRRIGATE",
                f"[{camp_id}] Richiesta irrigazione +{needed_water}%",
                state.get("date"),
                stats=state,
            )
            await mqtt.publish(ACTIVITY_LOGS_TOPIC, json.dumps(logs))

        if state["oxygenation"] < OXYGENATION_THRESHOLD and not state.get("reoxygenation_pending"):
            request_id = await request_reoxygenation(mqtt, camp_id)
            state["reoxygenation_pending"] = True
            state["reoxygenation_request_id"] = request_id

    except Exception as err:
        logger.error("Terrain telemetry error on %s: %s", camp_id, err, exc_info=True)


async def handle_irrigator_status(
    camp_id: str, raw_data: str, state: Dict[str, Any]
) -> None:
    """Track Irrigator availability and operation without changing terrain state."""
    try:
        data = json.loads(raw_data)
        if not isinstance(data, dict):
            return

        record_actuator_heartbeat(state, "irrigator", data)
        state["irrigator_operation"] = data.get("operation", "unknown")
        state["irrigation_active"] = data.get("operation") == "irrigating"

        logger.debug(
            "Irrigator status | field=%s | operation=%s | request=%s",
            camp_id,
            state["irrigator_operation"],
            data.get("active_request_id"),
        )
    except Exception as err:
        logger.error("Irrigator status error on %s: %s", camp_id, err, exc_info=True)


async def handle_dashboard_command(
    mqtt: aiomqtt.Client,
    camp_id: str,
    cmd: str,
    raw_data: str,
    state: Dict[str, Any],
) -> None:
    """Handle incoming control commands sent from the dashboard UI.

    Args:
        mqtt (aiomqtt.Client): Active MQTT connection client.
        camp_id (str): Target field camp identifier.
        cmd (str): Specific action string ('plant', 'irrigate', 'clear', etc.).
        raw_data (str): Command payload parameters.
        state (Dict[str, Any]): Field state record dictionary.
    """
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
        if not state.get("irrigation_pending"):
            target_min = state.get("min_moisture", 18.0) if state["occupied"] else EMPTY_FIELD_MIN_MOISTURE
            target_max = target_min + IRRIGATION_TARGET_MARGIN
            needed_water = round(max(MIN_IRRIGATION_AMOUNT, target_max - state["moisture"]), 1)
            request_id = await request_irrigation(mqtt, camp_id, needed_water)
            state["irrigation_pending"] = True
            state["irrigation_request_id"] = request_id

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
        if not state.get("reoxygenation_pending"):
            request_id = await request_reoxygenation(mqtt, camp_id)
            state["reoxygenation_pending"] = True
            state["reoxygenation_request_id"] = request_id

    elif cmd in ("reset", "restart"):
        state.clear()
        state.update(copy.deepcopy(DEFAULT_STATE))


async def listen_telemetry(
    mqtt: aiomqtt.Client,
    camp_states: Dict[str, Dict[str, Any]],
    auto_plant_tasks: Dict[str, asyncio.Task],
) -> None:
    """Subscribe to telemetry topics and route received messages to their respective handlers.

    Args:
        mqtt (aiomqtt.Client): Active MQTT subscriber client.
        camp_states (Dict[str, Dict[str, Any]]): Global state tracking map.
        auto_plant_tasks (Dict[str, asyncio.Task]): Tracking map for auto-planting background loops.
    """
    deduper = Deduper()

    await mqtt.subscribe("camp/+/environment/telemetry")
    await mqtt.subscribe("camp/+/plantation/status")
    await mqtt.subscribe("camp/+/terrain/telemetry")
    await mqtt.subscribe("camp/+/irrigator/status")
    await mqtt.subscribe("camp/+/camp_manager/cmd/#")

    async for message in mqtt.messages:
        topic = str(message.topic)
        raw_data = (
            message.payload.decode("utf-8")
            if isinstance(message.payload, bytes)
            else str(message.payload)
        )

        try:
            payload_obj = json.loads(raw_data)
            if isinstance(payload_obj, dict) and deduper.is_duplicate_or_stale(
                topic, payload_obj.get("ts")
            ):
                continue
        except Exception:
            pass

        topic_parts = topic.split("/")
        if len(topic_parts) >= 2 and topic_parts[0] == "camp":
            camp_id = topic_parts[1]
        else:
            continue

        if camp_id not in camp_states:
            camp_states[camp_id] = copy.deepcopy(DEFAULT_STATE)
            if camp_id not in auto_plant_tasks:
                auto_plant_tasks[camp_id] = asyncio.create_task(
                    auto_plant_monitor_loop(mqtt, camp_id, camp_states[camp_id])
                )

        state = camp_states[camp_id]

        try:
            if "environment" in topic:
                await handle_env_telemetry(raw_data, state)
            elif "plantation" in topic:
                await process_plantation_status(mqtt, camp_id, message.payload, state)
            elif "irrigator/status" in topic:
                await handle_irrigator_status(camp_id, raw_data, state)
            elif "terrain" in topic:
                await handle_terrain_telemetry(mqtt, camp_id, raw_data, state)
            elif "camp_manager/cmd/" in topic:
                command = topic.split("camp_manager/cmd/")[-1].lower()
                await handle_dashboard_command(mqtt, camp_id, command, raw_data, state)
        except Exception as err:
            logger.error(
                "Error processing topic %s: %s", topic, err, exc_info=True
            )


async def worker(camp_states: Dict[str, Dict[str, Any]]) -> None:
    """Initialize secure MQTT connection and manage concurrent background tasks.

    Args:
        camp_states (Dict[str, Dict[str, Any]]): Global dictionary holding camp states.

    Raises:
        Exception: Re-raises any unhandled task exception to prompt connection retry.
    """
    ssl_context = ssl.create_default_context(cafile=MQTT_CA_CERT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_context,
        identifier=MQTT_CLIENT_ID,
    )
    async with client:
        logger.info("Multi-camp service online.")

        auto_plant_tasks: Dict[str, asyncio.Task] = {}
        for camp_id in CONFIGURED_CAMPS:
            auto_plant_tasks[camp_id] = asyncio.create_task(
                auto_plant_monitor_loop(client, camp_id, camp_states[camp_id])
            )

        tasks = [
            asyncio.create_task(
                listen_telemetry(client, camp_states, auto_plant_tasks)
            ),
            asyncio.create_task(manager_heartbeat_loop(client, camp_states)),
            asyncio.create_task(system_health_monitor_loop(client, camp_states)),
        ] + list(auto_plant_tasks.values())

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                raise task.exception()


async def main() -> None:
    """Main function initializing states and managing reconnection loop."""
    camp_states = {camp_id: copy.deepcopy(DEFAULT_STATE) for camp_id in CONFIGURED_CAMPS}

    while True:
        try:
            await worker(camp_states)
        except Exception as error:
            logger.error("Connection dropped (%s). Reconnecting in %ss...", error, MQTT_RECONNECT_SECONDS)
            await asyncio.sleep(MQTT_RECONNECT_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())