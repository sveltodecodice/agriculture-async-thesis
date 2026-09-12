import random

RAIN_PROBS = {
    "winter": 0.3,
    "spring": 0.2,
    "summer": 0.1,
    "autumn": 0.3,
}


def get_weather_condition(season: str) -> str:
    """
    Generate a weather condition based on the given season.

    The probability of rain depends on the configured probability
    associated with the supplied season. 
    
    If rain is not generated, the weather condition is considered sunny.

    Args:
        season: Season used to determine the probability of rain.

    Returns:
        Either rain or sun

    Raises:
        ValueError: If the supplied season is not supported.
    """
    if season not in RAIN_PROBS:
        # non dovrebbe entrarci
        raise ValueError(
            f"Invalid season: {season}. "
            f"Expected one of: {', '.join(RAIN_PROBS)}."
        )

    rain_probability = RAIN_PROBS[season]

    if random.random() < rain_probability:
        return "rain"

    return "sun"