"""Temperature simulation calculations."""

import random

from common.constants import SEASONS_TEMP_RANGES


def get_temperature(season: str) -> int:
    """Generates a random temperature within configured seasonal bounds.

    Args:
        season (str): Target season name.

    Returns:
        int: Randomly generated temperature in degrees Celsius.

    Raises:
        ValueError: If season is not recognized in configuration.
    """
    if season not in SEASONS_TEMP_RANGES:
        raise ValueError(
            f"Invalid season: {season}. "
            f"Expected one of: {', '.join(SEASONS_TEMP_RANGES)}."
        )

    min_temp, max_temp = SEASONS_TEMP_RANGES[season]
    return random.randint(min_temp, max_temp)
