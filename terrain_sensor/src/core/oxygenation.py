import logging

logger = logging.getLogger(__name__)


def calculate_oxygenation(
    current_oxygenation: float, temperature: float, soil_moisture: float
) -> float:
    base_consumption = 3.0
    moisture_penalty = (soil_moisture / 100.0) * 1.7
    temp_penalty = max(0.0, (temperature - 15.0) * 0.1)

    daily_loss_oxygenation = base_consumption + moisture_penalty + temp_penalty
    new_oxygenation = current_oxygenation - daily_loss_oxygenation

    return round(max(0.0, min(100.0, new_oxygenation)), 1)


def apply_reoxygenation(
    current_oxygenation: float,
    minimal_oxygenation: float = 20.0,
    reoxygenation: float = 60.0,
) -> float:
    if current_oxygenation <= minimal_oxygenation:
        logger.info("Current oxygenation less than minimum, reoxygenation in progress")
        return round(min(100.0, current_oxygenation + reoxygenation), 1)
    return current_oxygenation
