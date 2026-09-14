from typing import Any, Dict


def start_irrigation(request: Any) -> Dict[str, float]:
    """Validate and normalize an irrigation command."""
    if isinstance(request, dict):
        amount = request.get("amount", 15.0)
    else:
        amount = request

    amount = float(amount)
    if amount <= 0:
        raise ValueError("Irrigation amount must be greater than zero")

    return {"amount": amount}


def start_reoxygenation() -> Dict[str, float]:
    """Return the resulting oxygenation after reoxygenation."""
    return {"oxygenation": 100.0}
