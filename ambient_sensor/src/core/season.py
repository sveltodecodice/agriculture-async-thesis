SEASONS_MAP = {
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
    12: "winter",
}
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
        raise ValueError(f"Invalid month number recieved: {month}. Expected a value from 1 to 12.")

    return SEASONS_MAP[month]