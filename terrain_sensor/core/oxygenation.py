def calculate_oxygenation(temperature: float, soil_moisture: float) -> float:
    moisture_penalty = soil_moisture * 0.35
    temp_penalty = max(0.0, (temperature - 15.0) * 0.7)

    oxygen = 100.0 - (moisture_penalty + temp_penalty)
    return round(max(0.0, min(100.0, oxygen)), 1)