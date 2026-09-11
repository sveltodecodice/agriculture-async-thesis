from core.irrigation import apply_irrigation

SOIL_FACTOR = {
    "Sandy": 1.15, "Sandy-Loam": 1.08, "Loam": 1.00, "Clay-Loam": 0.94, "Clay": 0.88,
}

def get_soil_moisture(
    current_moisture: float,
    weather: str,
    temperature: float,
    active_irrigation: bool = False,
    rain_mm: float = 0.0,
    radiation_wm2: float = 500.0,
    wind_kmh: float = 10.0,
    soil_type: str = "Loam",
) -> tuple[float, float]:
    factor = SOIL_FACTOR.get(soil_type, 1.0)

    if rain_mm > 0.0 or weather.lower() in ("rain", "rainy"):
        rain_val = rain_mm if rain_mm > 0.0 else 5.4
        change = rain_val * (2.5 / factor)
    else:
        evapotranspiration = ((temperature * 0.04) + (radiation_wm2 * 0.0015) + (wind_kmh * 0.01)) * factor
        change = -evapotranspiration

    new_moisture = current_moisture + change
    new_moisture, water_mm = apply_irrigation(new_moisture, active_irrigation, irrigated_amount=15.0)

    return round(max(0.0, min(100.0, new_moisture)), 1), round(water_mm, 1)