from core.calendar import get_max_days
from core.season import get_season
from core.temperature import get_temperature
from core.weather import get_weather_condition


def current_date(state: dict) -> str:
    return f"{state['day']:02d}/{state['month']:02d}/{state['year']}"

def create_timer_state(d=1, m=1, y=2026) -> dict:
    state = {
        "day": d,
        "month": m,
        "year": y,
        "season": "winter",
        "temperature": 12,
        "weather": "sun",
    }
    state["date"] = current_date(state)
    return state

def update_environment(state: dict):
    state["day"] += 1
    max_days = get_max_days(state["year"], state["month"])

#change the month if the day is over the max days

    if state["day"] > max_days:
        state["day"] = 1
        state["month"] += 1

#change the year if the n of month is over 12
        
        if state["month"] > 12:
            state["month"] = 1
            state["year"] += 1

    state["season"] = get_season(state["month"])
    state["temperature"] = get_temperature(state["season"])
    state["weather"] = get_weather_condition(state["season"])
    state["date"] = current_date(state)