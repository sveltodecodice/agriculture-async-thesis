from core.calendar import get_max_days
from core.season import get_season
from core.temperature import get_temperature
from core.weather import get_weather_condition


def create_timer_state(d=1, m=1, y=2026) -> dict:
    return {
        "day": d,
        "month": m,
        "year": y,
        "season": "winter",
        "temperature": 12,
        "weather": "sun",
    }


def update_environment(state: dict):
    state["day"] += 1
    max_days = get_max_days(state["year"], state["month"])

    if state["day"] > max_days:
        state["day"] = 1
        state["month"] += 1
        if state["month"] > 12:
            state["month"] = 1
            state["year"] += 1

    state["season"] = get_season(state["month"])
    state["temperature"] = get_temperature(state["season"])
    state["weather"] = get_weather_condition(state["season"])