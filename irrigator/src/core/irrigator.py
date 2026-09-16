"""Irrigation and reoxygenation domain execution logic."""

from typing import Any, Dict


def start_irrigation(request: Any) -> Dict[str, float]:
    """Validates and calculates irrigation volume.

    Args:
        request (Any): Dictionary containing 'amount' or a raw numerical/string value.

    Returns:
        Dict[str, float]: Dictionary containing the validated irrigation amount.

    Raises:
        ValueError: If amount is less than or equal to zero.
    """
    if isinstance(request, dict):
        amount = request.get("amount", 15.0)
    else:
        amount = request

    numeric_amount = float(amount)
    if numeric_amount <= 0:
        raise ValueError("Irrigation amount must be greater than zero")

    return {"amount": numeric_amount}


def start_reoxygenation() -> Dict[str, float]:
    """Executes soil reoxygenation and returns target oxygenation level.

    Returns:
        Dict[str, float]: Dictionary with resulting oxygenation percentage.
    """
    return {"oxygenation": 100.0}
