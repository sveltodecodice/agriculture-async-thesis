from typing import Any, Dict


def start_seeding(to_plant: Any) -> Dict[str, Any]:
    """
    Validate and normalize a seed command.
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
