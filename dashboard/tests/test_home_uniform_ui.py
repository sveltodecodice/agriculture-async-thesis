import sys
from pathlib import Path

sys.path.append("src")


def test_home_sections_share_the_same_visual_structure():
    source = Path("static/app.js").read_text(encoding="utf-8")

    assert 'function homeWeatherHTML()' in source
    assert 'function homeFieldsHTML()' in source
    assert '<div class="weather-head">' in source
    assert '<div class="weather-fields crop-fields">' in source
    assert 'class="weather-field crop-field"' in source
    assert 'class="weather-field-head"' in source
    assert 'class="weather-field-title"' in source
    assert 'class="weather-primary crop-primary"' in source
    assert 'class="weather-data crop-data"' in source
