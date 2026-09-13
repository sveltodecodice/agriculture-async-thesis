from datetime import date, timedelta
from typing import Any, Dict

from core.air_humidity import get_humidity_air, get_rain_mm
from core.radiation import get_radiation
from core.season import get_season
from core.temperature import get_temperature
from core.weather import get_weather_condition
from core.wind import get_wind_speed


class SensorManager:
    """Manages environmental state variables and advances time on a daily basis."""

    def __init__(self, day: int = 1, month: int = 1, year: int = 2026) -> None:
        """Initializes the sensor manager with a starting date.

        Args:
            day (int, optional): Initial day of the month. Defaults to 1.
            month (int, optional): Initial month of the year. Defaults to 1.
            year (int, optional): Initial calendar year. Defaults to 2026.
        """
        self.state = self._create_timer_state(day, month, year)

    def get_state(self) -> Dict[str, Any]:
        """Returns the current environmental state dictionary.

        Returns:
            Dict[str, Any]: Complete dictionary containing date and sensor metrics.
        """
        return self.state

    def get_formatted_date(self) -> str:
        """Formats the current simulation date into DD/MM/YYYY string format.

        Returns:
            str: Formatted date string (e.g., '01/01/2026').
        """
        current_date = date(
            self.state["year"],
            self.state["month"],
            self.state["day"],
        )
        return current_date.strftime("%d/%m/%Y")

    def _create_timer_state(
        self,
        day: int = 1,
        month: int = 1,
        year: int = 2026,
    ) -> Dict[str, Any]:
        """Creates and populates an initial state dictionary for a given date.

        Args:
            day (int, optional): Initial day of the month. Defaults to 1.
            month (int, optional): Initial month of the year. Defaults to 1.
            year (int, optional): Initial calendar year. Defaults to 2026.

        Returns:
            Dict[str, Any]: Initialized environment state dictionary.
        """
        initial_date = date(year, month, day)

        state = {
            "day": initial_date.day,
            "month": initial_date.month,
            "year": initial_date.year,
        }

        self.state = state
        self.refresh_environment()
        return self.state

    def refresh_environment(self) -> None:
        """Recalculates all environmental metrics based on the current date."""
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
        """Advances the simulation date by one day and refreshes environmental metrics."""
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
