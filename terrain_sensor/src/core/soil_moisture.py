"""Natural soil-moisture evolution.

Irrigation is intentionally NOT applied here. This module models only the
environmental evolution of the soil. Irrigation effects are applied once,
when the Terrain Sensor observes a completed event from the Irrigator.
"""

import logging
from common.constants import SOIL_FACTOR

logger = logging.getLogger(__name__)


def get_soil_moisture(
    current_moisture: float,
    temperature: float,
    rain_mm: float = 0.0,
    radiation_wm2: float = 500.0,
    wind_kmh: float = 10.0,
    soil_type: str = "Franco",
) -> float:
    """Calculate moisture changes caused only by rain and evapotranspiration."""
    st_key = str(soil_type).strip().lower().replace("_", "-")
    factor = SOIL_FACTOR.get(st_key) or SOIL_FACTOR.get(
        st_key.replace(" ", "-"), 1.0
    )

    if rain_mm > 0.0:
        change = rain_mm * (0.8 / factor)
    else:
        temp_term = max(0.2, temperature / 20.0)
        rad_term = max(0.2, radiation_wm2 / 400.0)
        wind_term = max(0.3, wind_kmh / 10.0)
        evapotranspiration = (5 * temp_term * rad_term * wind_term) * factor
        change = -evapotranspiration

    new_moisture = current_moisture + change
    logger.debug(
        "Natural soil moisture update | previous=%s | delta=%s | new=%s",
        current_moisture,
        change,
        new_moisture,
    )
    return round(max(0.0, min(100.0, new_moisture)), 1)
