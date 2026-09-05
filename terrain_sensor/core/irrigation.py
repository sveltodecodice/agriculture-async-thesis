def apply_irrigation(current_moisture: float, active: bool, irrigated: float = 20.0) -> float:
    if not active:
        return current_moisture
    return min(100.0, current_moisture + irrigated)