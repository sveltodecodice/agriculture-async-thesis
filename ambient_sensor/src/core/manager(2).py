from datetime import date, timedelta

from core.season import get_season
from core.temperature import get_temperature
from ambient_sensor.src.core.weatherold import get_weather_condition


class SensorManager:
    """
    Manage simulation date, season, temperature, and weather state.

    The manager keeps track of the current simulation date and derives
    environmental information such as season, temperature, and weather
    condition from that date.

    The supplied date is validated during initialization using
    :class:`datetime.date`.

    Attributes:
        state (dict): Dictionary containing the current simulation state.
            The dictionary contains the following keys:

            - day: Current day of the month.
            - month: Current month.
            - year: Current year.
            - season: Current season.
            - temperature: Current temperature.
            - weather: Current weather condition.
            - date: Current date formatted as DD/MM/YYYY.

    Raises:
        ValueError: If the supplied day, month, and year do not form a
            valid calendar date.
    """

    def __init__(self, d: int = 1, m: int = 1, y: int = 2026) -> None:
        """
        Initialize the sensor manager.

        Args:
            d (int): Initial day of the month. Defaults to 1.
            m (int): Initial month. Defaults to 1.
            y (int): Initial year. Defaults to 2026.

        Raises:
            ValueError: If the supplied date is invalid.
        """
        self.state = self._create_timer_state(d, m, y)
        
    def get_state(self):
        """
        Return current state object.
        
        Args: 
            None
        
        Returns:
            Dict: Current state in dictionary format
        
        Raises: 
            None
        """
        
        return self.state

    def get_formatted_date(self) -> str:
        """Return the current simulation date as a formatted string.

        Returns:
            str: Current date formatted as DD/MM/YYYY.

        Raises:
            ValueError: If the date stored in the state is invalid.
        """
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
        """
        Create and initialize the simulation state.

        The provided date is validated using :class:`datetime.date`.
        Environmental values are then calculated based on the initial
        month and season.

        Args:
            d (int): Initial day of the month. Defaults to 1.
            m (int): Initial month. Defaults to 1.
            y (int): Initial year. Defaults to 2026.

        Returns:
            dict: Initialized simulation state.

        Raises:
            ValueError: If the supplied date is invalid.
        """
        initial_date = date(y, m, d)

        self.state = {
            "day": initial_date.day,
            "month": initial_date.month,
            "year": initial_date.year,
        }

        self.refresh_environment()

        return self.state

    def refresh_environment(self) -> None:
        """
        Refresh environmental values for the current date.

        The season is derived from the current month. Temperature and
        weather condition are then calculated from the resulting season.

        The formatted date stored in the state is also refreshed.

        Returns:
            None
        """
        self.state["season"] = get_season(self.state["month"])
        self.state["temperature"] = get_temperature(self.state["season"])
        self.state["weather"] = get_weather_condition(self.state["season"])
        self.state["date"] = self.get_formatted_date()

    def update_environment(self) -> None:
        """
        Advance the simulation by one day and refresh the environment.

        Date progression is handled using :class:`datetime.timedelta`,
        which automatically manages month boundaries, year boundaries,
        and leap years.

        After advancing the date, season, temperature, weather, and the
        formatted date are recalculated.

        Returns:
            None
        """
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
