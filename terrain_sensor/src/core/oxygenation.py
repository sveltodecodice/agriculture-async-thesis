"""Natural soil oxygenation calculations."""

def calculate_oxygenation(
    current_oxygenation: float,
    temperature: float,
    soil_moisture: float,
) -> float:
    """Calculate natural oxygen depletion only.

    Reoxygenation is an Irrigator responsibility and is therefore applied
    only when a completed reoxygenation event is observed.
    """
    base_consumption = 3.0
    moisture_penalty = (soil_moisture / 100.0) * 1.7
    temp_penalty = max(0.0, (temperature - 15.0) * 0.1)

    daily_loss = base_consumption + moisture_penalty + temp_penalty
    new_oxygenation = current_oxygenation - daily_loss

    return round(max(0.0, min(100.0, new_oxygenation)), 1)
