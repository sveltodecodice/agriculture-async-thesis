from datetime import date, timedelta

from core.air_humidity import get_humidity_air, get_rain_mm
from core.radiation import get_radiation
from core.season import get_season
from core.temperature import get_temperature
from core.weather import get_weather_condition
from core.wind import get_wind_speed


class SensorManager:
    def __init__(self, d: int = 1, m: int = 1, y: int = 2026) -> None:
        self.state = self._create_timer_state(d, m, y)

    def get_state(self) -> dict:
        return self.state

    def get_formatted_date(self) -> str:
        current_date = date(
            self.state["year"],
            self.state["month"],
            self.state["day"],
        )
        return current_date.strftime("%d/%m/%Y")

    def _create_timer_state(
        self,
        d: int = 1,
        m: int = 1,
        y: int = 2026,
    ) -> dict:
        initial_date = date(y, m, d)

        self.state = {
            "day": initial_date.day,
            "month": initial_date.month,
            "year": initial_date.year,
        }

        self.refresh_environment()
        return self.state

    def refresh_environment(self) -> None:
        self.state["season"] = get_season(self.state["month"])
        self.state["temperature"] = get_temperature(self.state["season"])
        self.state["weather"] = get_weather_condition(self.state["season"])
        self.state["date"] = self.get_formatted_date()

        self.state["wind_kmh"] = get_wind_speed(
            self.state["season"], self.state["weather"]
        )
        self.state["radiation_wm2"] = get_radiation(
            self.state["season"], self.state["weather"]
        )
        self.state["humidity_air"] = get_humidity_air(self.state["weather"])
        self.state["rain_mm"] = get_rain_mm(self.state["weather"])

    def update_environment(self) -> None:
        current_date = date(
            self.state["year"],
            self.state["month"],
            self.state["day"],
        )

        next_day = current_date + timedelta(days=1)

        self.state["day"] = next_day.day
        self.state["month"] = next_day.month
        self.state["year"] = next_day.year

        self.refresh_environment()
