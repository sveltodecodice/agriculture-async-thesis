from common.constants import SEASONS_MAP


def get_season(month: int) -> str:
    """
    Return the season associated with a calendar month.

    Args:
        month: Calendar month number, from 1 to 12.

    Returns:
        The season associated with the given month.

    Raises:
        ValueError: If the month is outside the range 1 through 12.
    """
    if month not in SEASONS_MAP:
        raise ValueError(
            f"Invalid month number recieved: {month}. Expected a value from 1 to 12."
        )

    return SEASONS_MAP[month]
