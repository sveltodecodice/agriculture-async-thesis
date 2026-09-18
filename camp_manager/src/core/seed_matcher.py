from common.seeds import SEEDS_LST


def normalize_soil(value: str | None) -> str:
    """Normalize soil labels used by sensors and seed metadata."""
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def evaluate_season_ok(seed: dict, season: str | None) -> bool:
    """Return True when the crop supports the current season."""
    if not season:
        return False
    return str(season).lower() in [
        str(item).lower() for item in seed.get("seasons", [])
    ]


def evaluate_soil_ok(seed: dict, soil_type: str | None) -> bool:
    """Return True when the field matches the crop's ideal soil."""
    if not soil_type:
        return False
    return normalize_soil(seed.get("ideal_soil")) == normalize_soil(soil_type)


def find_top_3_seeds(
    moisture: float,
    season: str | None,
    soil_type: str | None = None,
) -> list[dict]:
    """Rank crops using season, soil compatibility and moisture.

    Priority is intentionally simple and deterministic:

    1. crops compatible with the current season;
    2. crops whose ``ideal_soil`` matches the observed field soil;
    3. smallest distance between current moisture and crop minimum;
    4. crop name as a stable tie-breaker.

    Manual planting remains possible even when soil does not match; this
    matcher is used for automatic/recommended crop selection only.
    """
    current_moisture = float(moisture)

    return sorted(
        SEEDS_LST,
        key=lambda seed: (
            0 if evaluate_season_ok(seed, season) else 1,
            0 if evaluate_soil_ok(seed, soil_type) else 1,
            abs(float(seed.get("min_soilmoisture", 20.0)) - current_moisture),
            str(seed.get("name", "")),
        ),
    )[:3]
