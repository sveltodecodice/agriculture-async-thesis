"""Harvest command parsing and validation logic."""

from typing import Any, Dict


def start_harvesting(request: Any) -> Dict[str, Any]:
    """Validates and normalizes an incoming harvest command payload.

    Args:
        request (Any): Incoming payload data expected to be a dictionary.

    Returns:
        Dict[str, Any]: Normalized dictionary containing seed and harvest date.

    Raises:
        ValueError: If the request is not a dictionary or missing seed identification.
    """
    if not isinstance(request, dict):
        raise ValueError("Harvest command must be a dictionary")

    seed_name = request.get("seed") or request.get("name")
    if not seed_name:
        raise ValueError("Harvest command must contain 'seed' or 'name'")

    return {
        "seed": str(seed_name).strip(),
        "date": request.get("date"),
    }
