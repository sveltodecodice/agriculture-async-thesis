from core.irrigation import apply_irrigation
from common.constants import SOIL_FACTOR

import logging

logger = logging.getLogger(__name__)


def get_soil_moisture(
    current_moisture: float,
    weather: str,
    temperature: float,
    active_irrigation: bool = False,
    rain_mm: float = 0.0,
    radiation_wm2: float = 500.0,
    wind_kmh: float = 10.0,
    soil_type: str = "Franco",
    irrigated_amount: float = 15.0,
) -> tuple[float, float]:

    st_key = str(soil_type).strip().lower().replace("_", "-")
    factor = SOIL_FACTOR.get(st_key) or SOIL_FACTOR.get(st_key.replace(" ", "-"), 1.0)

    if rain_mm > 0.0:
        # Ridotto leggermente l'impatto della pioggia per evitare saturazioni immediate
        change = rain_mm * (0.8 / factor)
    else:
        # Rimossi i blocchi rigidi max(0.8, ...) per permettere un'evaporazione reale
        # proporzionata alla scarsa radiazione invernale/nuvolosa
        temp_term = max(0.2, temperature / 20.0)
        rad_term = max(0.2, radiation_wm2 / 400.0)
        wind_term = max(0.3, wind_kmh / 10.0)

        # Aumentato il fattore base di evaporazione da 2.0 a 3.5 per smaltire l'acqua in eccesso
        evapotranspiration = (5 * temp_term * rad_term * wind_term) * factor
        change = -evapotranspiration

    new_moisture = current_moisture + change
    logger.info(
        f"New soil moisture: {new_moisture} | Previous moisture: {current_moisture} | Delta: {change}"
    )
    new_moisture, water_mm = apply_irrigation(
        new_moisture, active_irrigation, irrigated_amount=irrigated_amount
    )

    return round(max(0.0, min(100.0, new_moisture)), 1), round(water_mm, 1)
