import logging

logger = logging.getLogger(__name__)


def apply_irrigation(
    current_moisture: float, active: bool, irrigated_amount: float = 15.0
) -> tuple[float, float]:
    if not active:
        logging.warning("Irrigation requested for a not active field")
        return current_moisture, 0.0

    new_moisture = min(100.0, current_moisture + irrigated_amount)
    water_dispensed_mm = irrigated_amount
    return new_moisture, water_dispensed_mm
