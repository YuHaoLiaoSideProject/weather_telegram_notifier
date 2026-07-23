"""Open-Meteo data source implementation.

Free, no API key required.  Supports global locations via geocoding fallback.
"""

import logging
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from ..core.base import DataSource

logger = logging.getLogger(__name__)


# ── Shared HTTP session with retry ────────────────────────────────────────────

def _create_session() -> requests.Session:
    """Create a requests.Session with retry strategy and connection pooling."""
    retry_strategy = Retry(
        total=3,                     # max 3 retries
        backoff_factor=2,            # 2, 4, 8 seconds between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20,
    )
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# ── Taiwan major cities coordinates ──────────────────────────────────────────

CITY_COORDS = {
    "臺北市": (25.0330, 121.5654),
    "台北市": (25.0330, 121.5654),
    "松山區": (25.0497, 121.5642),
    "內湖區": (25.0837, 121.5882),
    "新北市": (25.0169, 121.4628),
    "桃園市": (24.9936, 121.3010),
    "臺中市": (24.1477, 120.6736),
    "台中市": (24.1477, 120.6736),
    "臺南市": (22.9997, 120.2270),
    "台南市": (22.9997, 120.2270),
    "高雄市": (22.6273, 120.3014),
    "基隆市": (25.1276, 121.7392),
    "新竹市": (24.8138, 120.9675),
    "新竹縣": (24.8392, 121.0089),
    "苗栗縣": (24.5602, 120.8223),
    "彰化縣": (24.0517, 120.5161),
    "南投縣": (23.8382, 120.9689),
    "雲林縣": (23.7092, 120.4313),
    "嘉義市": (23.4800, 120.4491),
    "嘉義縣": (23.4518, 120.2556),
    "屏東縣": (22.5496, 120.5488),
    "宜蘭縣": (24.7021, 121.7378),
    "花蓮縣": (23.9871, 121.6013),
    "臺東縣": (22.7584, 121.1441),
    "台東縣": (22.7584, 121.1441),
    "澎湖縣": (23.5711, 119.5793),
    "金門縣": (24.4368, 118.3190),
    "連江縣": (26.1504, 119.9506),
}

WMO_WEATHER_CODES = {
    0:  "☀️ 晴天",
    1:  "🌤 大致晴朗",
    2:  "⛅ 多雲時晴",
    3:  "☁️ 多雲",
    45: "🌫 霧",
    48: "🌫 霧淞",
    51: "🌦 小毛毛雨",
    53: "🌦 毛毛雨",
    55: "🌧 大雨毛毛雨",
    56: "🌧 凍毛毛雨",
    57: "🌧 凍大雨毛毛雨",
    61: "🌦 小雨",
    63: "🌧 雨",
    65: "🌧 大雨",
    66: "🌧 凍雨",
    67: "🌧 凍大雨",
    71: "🌨 小雪",
    73: "🌨 雪",
    75: "🌨 大雪",
    77: "🌨 雪粒",
    80: "🌦 陣雨",
    81: "🌧 中陣雨",
    82: "🌧 大陣雨",
    85: "🌨 小陣雪",
    86: "🌨 大陣雪",
    95: "⛈ 雷暴",
    96: "⛈ 雷暴加冰雹",
    99: "⛈ 雷暴加大冰雹",
}


class OpenMeteoDataSource(DataSource):
    """Weather data source using the free Open-Meteo API.

    No API key required.  For Taiwan cities the coordinates are hard-coded;
    other locations are resolved via the Open-Meteo geocoding API.
    """

    @property
    def name(self) -> str:
        return "openmeteo"

    def __init__(self):
        self._session = _create_session()

    def fetch(self, location: str, **kwargs) -> dict:
        session = self._session

        # ── Resolve coordinates ──────────────────────────────────────────
        coords = CITY_COORDS.get(location)
        if coords is None:
            # Fallback: use Open-Meteo geocoding API
            geo_url = "https://geocoding-api.open-meteo.com/v1/search"
            geo_params = {
                "name": location,
                "count": 1,
                "language": "zh",
                "format": "json",
            }
            geo_resp = session.get(geo_url, params=geo_params, timeout=15)
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()
            results = geo_data.get("results", [])
            if not results:
                raise ValueError(f"Location not found: {location!r}")
            lat = results[0]["latitude"]
            lon = results[0]["longitude"]
        else:
            lat, lon = coords

        # ── Fetch 7-day forecast ─────────────────────────────────────────
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "apparent_temperature_max,apparent_temperature_min,"
                "precipitation_probability_max,"
                "wind_speed_10m_max,wind_direction_10m_dominant"
            ),
            "timezone": "Asia/Taipei",
            "forecast_days": 7,
        }
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def parse(self, raw: dict, location: str) -> list[dict]:
        daily = raw.get("daily", {})
        if not daily:
            raise ValueError("No 'daily' data in Open-Meteo response")

        dates = daily.get("time", [])
        weather_codes = daily.get("weather_code", [])
        max_t = daily.get("temperature_2m_max", [])
        min_t = daily.get("temperature_2m_min", [])
        max_at = daily.get("apparent_temperature_max", [])
        min_at = daily.get("apparent_temperature_min", [])
        pop = daily.get("precipitation_probability_max", [])
        ws = daily.get("wind_speed_10m_max", [])
        wd = daily.get("wind_direction_10m_dominant", [])

        weekday_map = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        results: list[dict] = []

        for i, date_str in enumerate(dates):
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            code = weather_codes[i] if i < len(weather_codes) else None
            wx = (
                WMO_WEATHER_CODES.get(code, f"未知 ({code})")
                if code is not None
                else None
            )

            results.append({
                "location": location,
                "date": date_str,
                "weekday": weekday_map[dt.weekday()],
                "wx": wx,
                "pop": pop[i] if i < len(pop) else None,
                "max_t": max_t[i] if i < len(max_t) else None,
                "min_t": min_t[i] if i < len(min_t) else None,
                "max_at": max_at[i] if i < len(max_at) else None,
                "min_at": min_at[i] if i < len(min_at) else None,
                "rh": None,
                "ws": round(ws[i], 1) if i < len(ws) else None,
                "wd": _wind_direction(wd[i]) if i < len(wd) else None,
                "uvi": None,
                "description": None,
            })

        return results


def _wind_direction(degrees: float) -> str:
    """Convert wind direction in degrees to a Chinese compass direction."""
    directions = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"]
    index = round(degrees / 45) % 8
    return directions[index]
