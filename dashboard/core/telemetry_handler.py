live_state = {
    "gauges": [
        {"label": "Soil Moisture", "value": 0.0, "unit": "%", "color": "var(--blue)"},
        {"label": "Soil Oxygenation", "value": 0.0, "unit": "%", "color": "var(--green)"},
        {"label": "Days to Harvest", "value": 0, "unit": "days", "color": "var(--yellow)", "max": 60},
        {"type": "seed", "label": "Planted Seed", "seed": None, "icon": "🌱"}
    ],
    "weather": {"date": "--/--/----", "season": "spring", "temperature": 0, "is_raining": False},
    "trend": {
        "labels": [],
        "humidity": [],
        "temperature": []
    },
    "readings": [],
    "harvested": [],
    "recommended": [],
    "calendar": {
        "initialYear": 2026,
        "initialMonth": 0,
        "events": {}
    }
}

async def handle_telemetry_message(topic: str, payload: dict):
    
    
    if "environment/telemetry" in topic:
        current_date = payload.get("date", payload.get("data", "--"))
        temp = payload.get("temp", payload.get("temperatura", 0))
        is_rain = payload.get("weather") == "rain" or payload.get("piove", False)
        season = payload.get("season", payload.get("stagione", "spring"))
        
        live_state["weather"]["date"] = current_date
        live_state["weather"]["season"] = season
        live_state["weather"]["temperature"] = temp
        live_state["weather"]["is_raining"] = is_rain

        # Automatically log history & trend whenever the ambient date advances
        if current_date != "--" and current_date not in live_state["trend"]["labels"]:
            current_moisture = live_state["gauges"][0]["value"]
            
            # Push to Chart Trend (Humidity & Temperature)
            live_state["trend"]["labels"].append(current_date)
            live_state["trend"]["temperature"].append(temp)
            live_state["trend"]["humidity"].append(current_moisture)

            if len(live_state["trend"]["labels"]) > 15:
                live_state["trend"]["labels"].pop(0)
                live_state["trend"]["temperature"].pop(0)
                live_state["trend"]["humidity"].pop(0)

            # Log into Readings Table
            event_type = "irrigation" if is_rain else "none"
            live_state["readings"].insert(0, {
                "date": current_date,
                "moisture": f"{current_moisture}%",
                "event": event_type
            })
            if len(live_state["readings"]) > 10:
                live_state["readings"].pop()

            # Record event on Calendar Heatmap
            if is_rain:

                try:
                    parts = current_date.split("/")
                    if len(parts) == 3:
                        iso_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                        live_state["calendar"]["events"][iso_date] = "irrigation"
                except Exception:
                    pass


    elif "camp/terrain_telemetry" in topic:
        moisture = payload.get("soil_moisture", payload.get("umidita", 0.0))
        o2 = payload.get("oxygenation", payload.get("ossigeno", 0.0))
        live_state["gauges"][0]["value"] = round(float(moisture), 1)
        live_state["gauges"][1]["value"] = round(float(o2), 1)


    elif "plantation/status" in topic:
        occupied = payload.get("camp_availability", False)
        detail = payload.get("status_detail") or {}
        if occupied:
            live_state["gauges"][2]["value"] = detail.get("time_left", detail.get("giorni_rimasti", 0))
            live_state["gauges"][3]["seed"] = detail.get("plant_name", detail.get("seme", "Unknown"))
        else:
            live_state["gauges"][2]["value"] = 0
            live_state["gauges"][3]["seed"] = None


    elif "camp_manager/harvest" in topic:
        seed_name = payload.get("seed", payload.get("seme", "Crop"))
        live_state["harvested"].insert(0, {
            "seed": seed_name.capitalize(),
            "date": live_state["weather"]["date"],
            "color": "var(--yellow-soft)"
        })

    elif "camp_manager/recommendations" in topic:
        # Accepts raw advice calculated by camp_manager/advisor microservices
        recs = payload.get("recommendations", payload.get("top3", []))
        formatted_recs = []
        for item in recs[:3]:
            formatted_recs.append({
                "seed": item.get("seed", item.get("nome", "Seed")).capitalize(),
                "reason": item.get("reason", item.get("motivo", "Optimal growth conditions")),
                "score": f"{item.get('score', item.get('punteggio', 90))}%"
            })
        live_state["recommended"] = formatted_recs