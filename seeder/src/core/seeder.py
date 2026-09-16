"""Validation and normalization logic for incoming seed commands."""

from typing import Any, Dict


def start_seeding(to_plant: Any) -> Dict[str, Any]:
    """Validates and normalizes a seed command payload.

    Args:
        to_plant (Any): Raw seed command string or dictionary.

    Returns:
        Dict[str, Any]: Normalized seed data dictionary.

    Raises:
        ValueError: If input format is unsupported or seed name is missing.
    """
    if isinstance(to_plant, str):
        seed_name = to_plant.strip()
        if not seed_name:
            raise ValueError("Seed name cannot be empty")
        return {"name": seed_name}

    if isinstance(to_plant, dict):
        seed_name = to_plant.get("name") or to_plant.get("seed")
        if not seed_name:
            raise ValueError("Seed command must contain 'name' or 'seed'")

        seed_data = dict(to_plant)
        seed_data["name"] = str(seed_name).strip()
        return seed_data

    raise ValueError("Seed command must be a string or a dictionary")
