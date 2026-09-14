from typing import Any, Dict


def start_harvesting(request: Any) -> Dict[str, Any]:
    """Validate and normalize a harvest command."""
    if not isinstance(request, dict):
        raise ValueError("Harvest command must be a dictionary")

    seed_name = request.get("seed") or request.get("name")
    if not seed_name:
        raise ValueError("Harvest command must contain 'seed' or 'name'")

    return {
        "seed": str(seed_name).strip(),
        "date": request.get("date"),
    }
