"""Sensor management state and simulation controller."""

from datetime import date, timedelta
from typing import Any, Dict

from core.air_humidity import get_humidity_air, get_rain_mm
from core.radiation import get_radiation
from core.season import get_season
from core.temperature import get_temperature
from core.weather import get_weather_condition
from core.wind import get_wind_speed


class SensorManager:
    """Manages environmental telemetry state and date progression."""

    def __init__(self, day: int = 1, month: int = 1, year: int = 2026) -> None:
        """Initializes the sensor manager to a start date.

        Args:
            day (int): Initial day of month. Defaults to 1.
            month (int): Initial month of year. Defaults to 1.
            year (int): Initial calendar year. Defaults to 2026.
        """
        self.state: Dict[str, Any] = {}
        self.reset(day, month, year)

    def get_state(self) -> Dict[str, Any]:
        """Returns current environmental metrics and date.

        Returns:
            Dict[str, Any]: Environmental state dictionary.
        """
        return self.state

    def get_formatted_date(self) -> str:
        """Formats the simulation date into DD/MM/YYYY.

        Returns:
            str: Formatted date string.
        """
        current_date = date(
            self.state["year"],
            self.state["month"],
            self.state["day"],
        )
        return current_date.strftime("%d/%m/%Y")

    def reset(self, day: int = 1, month: int = 1, year: int = 2026) -> Dict[str, Any]:
        """Resets environmental metrics and date state to specified date.

        Args:
            day (int): Target day. Defaults to 1.
            month (int): Target month. Defaults to 1.
            year (int): Target year. Defaults to 2026.

        Returns:
            Dict[str, Any]: Updated environment state dictionary.
        """
        initial_date = date(year, month, day)
        self.state = {
            "day": initial_date.day,
            "month": initial_date.month,
            "year": initial_date.year,
        }
        self.refresh_environment()
        return self.state

    def refresh_environment(self) -> None:
        """Recalculates environmental readings for the current date state."""
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
        """Advances simulation state by one day and updates metrics."""
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
