"""Apply the observed result of an Irrigator operation."""

def apply_irrigation(current_moisture: float, amount: float) -> float:
    """Apply one completed irrigation event to simulated soil moisture."""
    numeric_amount = float(amount)
    if numeric_amount <= 0:
        raise ValueError("Irrigation amount must be greater than zero")
    return round(min(100.0, current_moisture + numeric_amount), 1)
