"""Seasonal lookup logic."""

from common.constants import MONTH_NUM_SEASON_MAP


def get_season(month: int) -> str:
    """Determines the season associated with a calendar month number.

    Args:
        month (int): Month number (1 to 12).

    Returns:
        str: Associated season name.

    Raises:
        ValueError: If the month integer is not between 1 and 12.
    """
    if month not in MONTH_NUM_SEASON_MAP:
        raise ValueError(
            f"Invalid month number received: {month}. Expected a value from 1 to 12."
        )

    return MONTH_NUM_SEASON_MAP[month]
