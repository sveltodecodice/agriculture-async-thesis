"""Irrigation and reoxygenation actuator domain logic."""

from typing import Any, Dict


def start_irrigation(request: Any) -> Dict[str, float]:
    """Validate the requested soil-moisture percentage-point increase."""
    if isinstance(request, dict):
        amount = request.get("amount_pct", request.get("amount", 15.0))
    else:
        amount = request

    numeric_amount = float(amount)
    if numeric_amount <= 0:
        raise ValueError("Irrigation amount must be greater than zero")

    return {
        "amount_pct": numeric_amount,
        # Compatibility alias for older Terrain Sensor versions.
        "amount": numeric_amount,
    }


def start_reoxygenation(target: float = 100.0) -> Dict[str, float]:
    """Return the target oxygenation after actuator completion."""
    return {"oxygenation": float(target)}
