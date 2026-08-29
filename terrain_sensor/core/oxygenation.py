def calculate_oxygenation(soil_moisture: float, temperature: float) -> float:
    """
    Starts at a baseline of 100% and decreases based on soil moisture saturation 
    and elevated ambient temperatures.
    """
    moisture_penalty = soil_moisture * 0.35
    temp_penalty = max(0.0, (temperature - 15.0) * 0.7)

    new_oxygen = 100.0 - (moisture_penalty + temp_penalty)
    return round(max(0.0, min(100.0, new_oxygen)), 1)