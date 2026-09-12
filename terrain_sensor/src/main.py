import asyncio
import json
import logging
import ssl
import aiomqtt

from common.parameters import (
    MQTT_HOST,
    MQTT_PASS,
    MQTT_PORT,
    MQTT_USER,
)
from utils.logger_utils import LoggingUtils
from utils.mqtt_utils import Deduper, publish_json
from core.terrain_condition import create_terrain_state, process_terrain_update
from common.constants import KNOWN_CAMPS

LoggingUtils.configure(
    console_level=logging.INFO,
)

logger = LoggingUtils.get_logger(__name__)


async def listen_mqtt_telemetry(client, camp_states, dedup):
    await client.subscribe("camp/+/environment/telemetry")
    await client.subscribe("camp/+/terrain/cmd/#")

    async for msg in client.messages:
        top = str(msg.topic)
        raw = (
            msg.payload.decode("utf-8")
            if isinstance(msg.payload, bytes)
            else str(msg.payload)
        )

        parts = top.split("/")
        if len(parts) >= 2 and parts[0] == "camp":
            camp_id = parts[1]
        else:
            continue

        if camp_id not in camp_states:
            camp_states[camp_id] = create_terrain_state(
                initial_moisture=28.0, initial_oxygen=70.0, soil_type="Franco"
            )

        state = camp_states[camp_id]

        if "environment/telemetry" in top:
            logger.debug("Fetched telemetry")
            ambient_data = json.loads(raw)
            if dedup.is_duplicate_or_stale(top, ambient_data.get("ts")):
                continue

            telemetry = process_terrain_update(state, ambient_data)
            out_topic = f"camp/{camp_id}/terrain/telemetry"

            await publish_json(client, out_topic, telemetry, qos=1)
            logger.info(
                f"[{camp_id.upper()}] [{telemetry['date']}] Soil: {telemetry.get('soil_type', 'Franco')} | "
                f"Moisture: {telemetry['soil_moisture']:.1f}% | O2: {telemetry['oxygenation']:.1f}% | "
                f"Pump: {telemetry['irrigation_active']}",
            )

        elif "terrain/cmd/" in top:
            cmd = top.split("terrain/cmd/")[-1].lower()

            if cmd in ("irrigate", "force_irrigate", "force_irrigation"):
                amount = 15.0
                try:
                    if raw and not raw.startswith("{"):
                        amount = float(raw)
                except ValueError:
                    pass

                state["soil_moisture"] = min(100.0, state["soil_moisture"] + amount)
                state["water_dispensed_mm"] = amount
                state["irrigation_active"] = False
                logger.info(
                    f"[{camp_id.upper()}] Irrigated (+{amount:.1f}%)! New moisture: {state['soil_moisture']:.1f}%.",
                )

            elif cmd in ("reoxygenate", "oxygen"):
                state["oxygenation"] = 100.0
                logger.info(
                    f"[{camp_id.upper()}] Soil reoxygenated to 100.0%.",
                )

            elif cmd in ("set_soil_type", "set_type"):
                state["soil_type"] = raw.strip()
                logger.info(
                    f"[{camp_id.upper()}] Soil type set to: {state['soil_type']}",
                )

            elif cmd in ("reset", "restart"):
                state["soil_moisture"] = 28.0
                state["oxygenation"] = 70.0
                state["soil_type"] = "Franco"
                state["irrigation_active"] = False
                dedup.reset()
                logger.info(
                    f"[{camp_id.upper()}] Terrain state reset to 28.0%.",
                )

            telemetry = {
                "soil_moisture": state["soil_moisture"],
                "oxygenation": state["oxygenation"],
                "soil_type": state.get("soil_type", "Franco"),
                "irrigation_active": state["irrigation_active"],
                "date": state.get("date", "01/01/2026"),
            }
            out_topic = f"camp/{camp_id}/terrain/telemetry"
            await publish_json(client, out_topic, telemetry, qos=1)


async def worker(camp_states, dedup):
    ssl_ctx = ssl.create_default_context(cafile="/app/certs/ca.crt")
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    client = aiomqtt.Client(
        MQTT_HOST,
        MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=ssl_ctx,
        identifier="terrain-sensor-app",
    )
    async with client:
        logger.info("Multi-camp service online. Starting tasks...")

        t1 = asyncio.create_task(listen_mqtt_telemetry(client, camp_states, dedup))

        done, pending = await asyncio.wait([t1], return_when=asyncio.FIRST_EXCEPTION)

        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        for task in done:
            if task.exception():
                raise task.exception()


async def main():

    camp_states = {
        cid: create_terrain_state(
            initial_moisture=28.0, initial_oxygen=70.0, soil_type="Franco"
        )
        for cid in KNOWN_CAMPS
    }
    dedup = Deduper()

    while True:
        try:
            await worker(camp_states, dedup)
        except Exception as err:
            logger.error(
                f"Connection dropped ({err}). Reconnecting in 5s...",
            )
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
