"""
Streamlit dashboard for the simulated farm camp.
"""

import asyncio
import json
import logging
import os
import threading
from collections import deque
from datetime import datetime

import aiomqtt
import streamlit as st


MQTT_HOST = os.getenv("MQTT_BROKER_HOST", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_BROKER_USER", "farm_admin")
MQTT_PASS = os.getenv("MQTT_BROKER_PASS", "secure_farm")

ENV_TOPIC = "environment/telemetry"
TERRAIN_TOPIC = "camp/terrain_telemetry"
PLANTATION_TOPIC = "plantation/status"
NOTIFICATION_TOPIC = "camp/notifications"
ACTIVITY_TOPIC = "camp/activity_logs"
HARVEST_TOPIC = "camp/harvest_deposit"
TOP_SEEDS_TOPIC = "camp/top_seeds"

ALL_TOPICS = (
    ENV_TOPIC,
    TERRAIN_TOPIC,
    PLANTATION_TOPIC,
    NOTIFICATION_TOPIC,
    ACTIVITY_TOPIC,
    HARVEST_TOPIC,
    TOP_SEEDS_TOPIC,
)

COMMAND_TOPICS = {
    "plant": "camp_manager/cmd/plant",
    "irrigate": "camp_manager/cmd/irrigate",
    "clear": "camp_manager/cmd/clear",
    "skip": "camp_manager/cmd/skip",
    "reoxygenate": "camp_manager/cmd/reoxygenate",
    "reset": "camp_manager/cmd/reset",
}

log = logging.getLogger("farm-dashboard")


class FarmBridge:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = {
            "environment": {},
            "terrain": {},
            "plantation": {},
            "notifications": deque(maxlen=30),
            "activity": [],
            "harvest": [],
            "top_seeds": "",
            "connected": False,
            "last_message": None,
            "command_status": "",
        }
        self.loop = None
        self.thread = threading.Thread(
            target=self._run, daemon=True, name="mqtt-dashboard"
        )
        self.thread.start()

    def _run(self):
        asyncio.run(self._worker())

    async def _worker(self):
        while True:
            try:
                client = aiomqtt.Client(
                    MQTT_HOST,
                    MQTT_PORT,
                    username=MQTT_USER,
                    password=MQTT_PASS,
                    keepalive=30,
                )
                async with client:
                    self.loop = asyncio.get_running_loop()

                    for topic in ALL_TOPICS:
                        await client.subscribe(topic, qos=1)

                    self._set("connected", True)
                    print("[DASHBOARD] MQTT connected successfully.", flush=True)

                    async for message in client.messages:
                        await self._handle(message)

            except Exception as exc:
                self._set("connected", False)
                print(f"[DASHBOARD] MQTT connection error: {exc}. Retrying in 5s...", flush=True)
                await asyncio.sleep(5)

    async def _handle(self, message):
        topic = str(message.topic)
        raw = message.payload.decode("utf-8", errors="replace")
        self._set("last_message", datetime.now().strftime("%H:%M:%S"))

        if topic == ENV_TOPIC:
            self._update_json("environment", raw)
        elif topic == TERRAIN_TOPIC:
            self._update_json("terrain", raw)
        elif topic == PLANTATION_TOPIC:
            self._update_json("plantation", raw)
        elif topic == NOTIFICATION_TOPIC:
            self._append("notifications", raw)
        elif topic == ACTIVITY_TOPIC:
            self._set_list("activity", raw)
        elif topic == HARVEST_TOPIC:
            self._set_list("harvest", raw)
        elif topic == TOP_SEEDS_TOPIC:
            self._set("top_seeds", raw)

    def _update_json(self, key, raw):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return
        if isinstance(value, dict):
            with self.lock:
                self.state[key] = value

    def _set_list(self, key, raw):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = []
        if isinstance(value, list):
            self._set(key, value)

    def _append(self, key, value):
        with self.lock:
            self.state[key].appendleft(value)

    def _set(self, key, value):
        with self.lock:
            self.state[key] = value

    def snapshot(self):
        with self.lock:
            result = dict(self.state)
            result["notifications"] = list(self.state["notifications"])
            return result

    def publish(self, command, payload):
        topic = COMMAND_TOPICS[command]
        if self.loop is None:
            return False

        future = asyncio.run_coroutine_threadsafe(
            self._publish(topic, payload), self.loop
        )
        try:
            future.result(timeout=5)
        except Exception as exc:
            self._set("command_status", f"Command failed: {exc}")
            return False

        self._set("command_status", f"Command sent: {command}")
        return True

    async def _publish(self, topic, payload):
        client = aiomqtt.Client(
            MQTT_HOST,
            MQTT_PORT,
            username=MQTT_USER,
            password=MQTT_PASS,
            keepalive=30,
        )
        async with client:
            await client.publish(topic, payload=str(payload), qos=1)


@st.cache_resource
def get_bridge():
    return FarmBridge()


def number(data, key, default=0):
    value = data.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def show_metric(label, value, suffix=""):
    st.metric(label, f"{value}{suffix}")


def render_status(state):
    env = state["environment"]
    terrain = state["terrain"]
    plantation = state["plantation"]

    columns = st.columns(5)

    with columns[0]:
        show_metric("Temperature", number(env, "temperature"), " °C")

    with columns[1]:
        show_metric("Soil moisture", number(terrain, "soil_moisture"), " %")

    with columns[2]:
        show_metric("Oxygenation", number(terrain, "oxygenation"), " %")

    with columns[3]:
        active = terrain.get("irrigation_active", False)
        st.metric("Irrigation", "ACTIVE" if active else "OFF")

    with columns[4]:
        detail = plantation.get("status_detail") or {}
        st.metric("Crop", detail.get("plant_name", "None"))


def send_command(bridge, button_label, command, payload):
    if st.sidebar.button(button_label):
        if not bridge.publish(command, payload):
            st.sidebar.error("MQTT command failed")


def render_controls(bridge, state):
    st.sidebar.header("Farm Control")

    seed = st.sidebar.text_input("Seed", value="tomato")
    send_command(bridge, "Plant", "plant", seed.lower())
    send_command(bridge, "Force irrigation", "irrigate", "trigger")

    days = st.sidebar.number_input("Skip days", min_value=1, max_value=30, value=1)
    send_command(bridge, "Skip days", "skip", int(days))

    send_command(bridge, "Reoxygenate soil", "reoxygenate", "trigger")
    send_command(bridge, "Clear camp", "clear", "trigger")

    st.sidebar.divider()
    send_command(bridge, "RESET SYSTEM", "reset", "trigger")

    if state.get("command_status"):
        st.sidebar.caption(state["command_status"])


def render_monitoring(state):
    st.subheader("Live monitoring")
    render_status(state)

    left, right = st.columns(2)

    with left:
        st.write("Environment")
        st.json(state["environment"])

    with right:
        st.write("Terrain")
        st.json(state["terrain"])

    st.write("Plantation status")
    st.json(state["plantation"])


def render_harvest(state):
    st.subheader("Harvest history")

    history = state["harvest"]
    if not history:
        st.info("No harvest history is available yet.")
        return

    rows = [item if isinstance(item, dict) else {"event": item} for item in history]
    st.dataframe(rows, use_container_width=True)


def render_logs(state):
    st.subheader("Activity")

    notifications = state["notifications"]
    activity = state["activity"]

    if notifications:
        st.write("Notifications")
        for item in notifications[:10]:
            st.info(str(item))

    if activity:
        st.write("Activity log")
        st.dataframe(list(reversed(activity)), use_container_width=True)
    else:
        st.info("No activity received yet.")


def render_map(state):
    st.subheader("Farm location")
    st.info("The current repository exposes one simulated camp.")


def main():
    st.set_page_config(page_title="Smart Farming Dashboard", layout="wide")

    bridge = get_bridge()
    state = bridge.snapshot()

    st.title("Smart Farming Dashboard")

    if state["connected"]:
        st.success("MQTT connected")
    else:
        st.warning("MQTT disconnected - retrying automatically")

    if state["last_message"]:
        st.caption(f"Last MQTT message: {state['last_message']}")

    render_controls(bridge, state)

    monitoring, map_tab, harvest, logs = st.tabs(
        ["Monitoring", "Map", "Harvest", "Activity"]
    )

    with monitoring:
        render_monitoring(state)
    with map_tab:
        render_map(state)
    with harvest:
        render_harvest(state)
    with logs:
        render_logs(state)


if __name__ == "__main__":
    main()