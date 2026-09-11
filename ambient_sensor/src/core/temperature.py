import random

SEASON_RANGES = {
    "autumn": (16, 22),
    "winter": (12, 16),
    "spring": (20, 25),
    "summer": (28, 35),
}


def get_temperature(season: str) -> int:
    """
    Generate a temperature appropriate for the given season.

    Args:
        season: Name of the season. Expected values are:
                    1. autumn
                    2. winter
                    3. spring
                    4. summer

    Returns:
        A randomly generated temperature within the configured range
        for the given season.

    Raises:
        ValueError: If the supplied season is not supported.
    """
    if season not in SEASON_RANGES:
        # ! non dovrebbe mai entrare qui
        raise ValueError(
            f"Invalid season: {season}. "
            f"Expected one of: {', '.join(SEASON_RANGES)}."
        )

    min_temp, max_temp = SEASON_RANGES[season]
    return random.randint(min_temp, max_temp)