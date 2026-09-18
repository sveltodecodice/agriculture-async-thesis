"""Temperature simulation calculations."""

import random

from common.constants import SEASON_TEMPERATURE_RANGES


def get_temperature(season: str) -> int:
    """Generates a random temperature within configured seasonal bounds.

    Args:
        season (str): Target season name.

    Returns:
        int: Randomly generated temperature in degrees Celsius.

    Raises:
        ValueError: If season is not recognized in configuration.
    """
    if season not in SEASON_TEMPERATURE_RANGES:
        raise ValueError(
            f"Invalid season: {season}. "
            f"Expected one of: {', '.join(SEASON_TEMPERATURE_RANGES)}."
        )

    min_temp, max_temp = SEASON_TEMPERATURE_RANGES[season]
    return random.randint(min_temp, max_temp)
