from common.seeds import SEEDS_LST


def evaluate_season_ok(seed: dict, season: str) -> bool:
    """Check if a crop is suitable for planting in the given season.

    Args:
        seed (dict): Dictionary containing seed metadata and supported seasons.
        season (str): Name of the current season (e.g., "spring", "estate").

    Returns:
        bool: True if the crop can be grown in the target season, False otherwise.
    """
    if not season:
        return False
    return season.lower() in [s.lower() for s in seed.get("seasons", [])]


def find_top_3_seeds(moisture: float, season: str) -> list[dict]:
    """Find the top 3 best matching seeds for the current soil moisture and season.

    The algorithm first filters crops that match the current season. Then it sorts
    them based on how close their minimum required moisture is to the actual soil moisture.

    Args:
        moisture (float): Current soil moisture percentage.
        season (str): Current active season.

    Returns:
        list[dict]: A list containing up to 3 best-matching seed dictionaries.
    """
    seasonal_matches = [s for s in SEEDS_LST if evaluate_season_ok(s, season)]
    candidate_list = seasonal_matches if len(seasonal_matches) >= 3 else SEEDS_LST

    return sorted(
        candidate_list, key=lambda s: abs(s.get("min_soilmoisture", 20.0) - moisture)
    )[:3]
