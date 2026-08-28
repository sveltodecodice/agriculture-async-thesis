def get_soil_moisture(current_moisture: float, weather: str, temperature: float) -> float:
    if weather == "rain":
        change = 8.0
    else:
        base_drying = 4.0 if weather == "sun" else 0.2
        temp_multiplier = max(0.2, temperature / 20.0)
        change = -(base_drying * temp_multiplier)

    new_moisture = current_moisture + change

    return round(max(0.0, min(100.0, new_moisture)), 1)