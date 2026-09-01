live_state = {
    "gauges": [
        {"label": "Soil Moisture", "value": 50, "unit": "%", "color": "var(--blue)"},
        {"label": "Soil Oxygenation", "value": 80, "unit": "%", "color": "var(--green)"},
        {"label": "Days to Harvest", "value": 0, "unit": "days", "color": "var(--yellow)", "max": 60},
        {"type": "seed", "label": "Planted Seed", "seed": None, "icon": "🌱"}
    ],
    "weather": {"date": "01/01/2026", "season": "winter", "temperature": 12, "is_raining": False},
    "trend": {"labels": [], "humidity": [], "temperature": []},
    "readings": [],
    "harvested": [],
    "recommended": []
}

async def handle_telemetry_message(topic, payload):
    if "environment/telemetry" in topic:
        live_state["weather"]["date"] = payload.get("date", "--")
        live_state["weather"]["season"] = payload.get("season", "winter")
        live_state["weather"]["temperature"] = payload.get("temp", 15)
        live_state["weather"]["is_raining"] = payload.get("weather") == "rain"
        
    elif "camp/terrain_telemetry" in topic:
        moisture = payload.get("soil_moisture", 50.0)
        o2 = payload.get("oxygenation", 80.0)
        live_state["gauges"][0]["value"] = round(moisture, 1)
        live_state["gauges"][1]["value"] = round(o2, 1)
        
    elif "plantation/status" in topic:
        occupied = payload.get("camp_availability", False)
        detail = payload.get("status_detail") or {}
        if occupied:
            live_state["gauges"][2]["value"] = detail.get("time_left", 0)
            live_state["gauges"][3]["seed"] = detail.get("plant_name")
        else:
            live_state["gauges"][2]["value"] = 0
            live_state["gauges"][3]["seed"] = None