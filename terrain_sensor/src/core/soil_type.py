"""Initial soil-layout selection for replicated terrain sensors."""

import random

from common.constants import DEFAULT_FIELD_ORDER, SOIL_TYPES


def normalize_soil(value: str) -> str:
    return str(value or "").strip().lower().replace("_", "-").replace(" ", "-")


def select_initial_soil(
    field_name: str,
    configured_type: str,
    layout_seed: int,
) -> str:
    """Resolve the initial soil type for one field.

    Explicit soil types are preserved. ``random`` / ``auto`` use a
    deterministic shuffled layout so field_a, field_b and field_c receive
    different soil types while restarts remain reproducible.
    """
    configured = str(configured_type or "Franco").strip()
    if normalize_soil(configured) not in {"random", "auto"}:
        return configured

    soils = list(SOIL_TYPES)
    random.Random(int(layout_seed)).shuffle(soils)

    try:
        field_index = DEFAULT_FIELD_ORDER.index(field_name)
    except ValueError:
        # Deterministic fallback for additional field IDs. Current A/B/C
        # topology uses the guaranteed-unique branch above.
        field_index = sum(ord(char) for char in str(field_name))

    return soils[field_index % len(soils)]
