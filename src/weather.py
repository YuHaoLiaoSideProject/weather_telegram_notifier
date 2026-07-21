"""
Weather data fetcher.
Supports two data sources:
  1. Taiwan CWB (Central Weather Bureau) Open Data API
  2. Open-Meteo API (free, no API key required, global coverage)
"""

import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests


# ─── CWB Weather API (Taiwan) ────────────────────────────────────────────────

CWB_API_BASE = "https://opendata.cwb.gov.tw/api/v1/rest/datastore"
# 鄉鎮天氣預報 - 台灣未來 1 週天氣預報
CWB_DATASET_ID = "F-D0047-091"

# Mapping of common location names to their geocode in the CWB dataset
CWB_LOCATIONS = {
    "臺北市":   "63",
    "台北市":   "63",
    "新北市":   "65",
    "桃園市":   "68",
    "臺中市":   "66",
    "台中市":   "66",
    "臺南市":   "67",
    "台南市":   "67",
    "高雄市":   "64",
    "基隆市":   "69",
    "新竹市":   "70",
    "新竹縣":   "16",
    "苗栗縣":   "13",
    "彰化縣":   "07",
    "南投縣":   "10",
    "雲林縣":   "09",
    "嘉義市":   "72",
    "嘉義縣":   "20",
    "屏東縣":   "14",
    "宜蘭縣":   "17",
    "花蓮縣":   "19",
    "臺東縣":   "18",
    "台東縣":   "18",
    "澎湖縣":   "22",
    "金門縣":   "30",
    "連江縣":   "32",
}


def fetch_cwb_forecast(
    location_name: str,
    api_key: Optional[str] = None,
) -> dict:
    """Fetch weekly forecast from Taiwan CWB Open Data API.

    Args:
        location_name: City/district name (e.g. "臺北市", "高雄市").
        api_key: CWB API authorization key.  Falls back to CWB_API_KEY env var.

    Returns:
        Raw JSON response from the CWB API.

    Raises:
        ValueError: If location is not found or API key is missing.
        requests.RequestException: On network / HTTP errors.
    """
    if api_key is None:
        api_key = os.environ.get("CWB_API_KEY")
    if not api_key:
        raise ValueError(
            "CWB API key is required.  Set CWB_API_KEY environment variable."
        )

    geocode = CWB_LOCATIONS.get(location_name)
    if geocode is None:
        raise ValueError(
            f"Unknown location: {location_name!r}. "
            f"Available: {', '.join(sorted(set(k for k in CWB_LOCATIONS if len(k) == 3)))}"
        )

    url = f"{CWB_API_BASE}/{CWB_DATASET_ID}"
    params = {
        "Authorization": api_key,
        "locationName": location_name,
        "elementName": (
            "PoP12h,T,RH,MinCI,WS,MaxAT,Wx,MaxCI,"
            "MinT,UVI,WeatherDescription,MinAT,MaxT,WD,Td"
        ),
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_cwb_forecast(raw: dict) -> list[dict]:
    """Parse CWB API response into a list of daily forecast entries.

    Each entry contains:
        date, weekday, location,
        wx (weather phenomenon), pop (rain probability),
        max_t, min_t, max_at (apparent temp), min_at,
        rh (humidity), ws (wind speed), wd (wind direction),
        description (summary text)
    """
    records = raw.get("records", {})
    locations = records.get("locations", [])
    if not locations:
        raise ValueError("No 'locations' found in CWB response")

    location_data = locations[0].get("location", [])
    if not location_data:
        raise ValueError("No location data found in CWB response")

    loc = location_data[0]
    loc_name = loc.get("locationName", "未知")
    weather_elements = loc.get("weatherElement", [])

    # Build a dict: element_name -> list of time-slot entries
    elements: dict[str, list[dict]] = {}
    for elem in weather_elements:
        ele_name = elem.get("elementName", "")
        elements[ele_name] = elem.get("time", [])

    # We'll group by start_time (date) and collect all element values
    # Use the "T" (temperature) element's time slots as the reference timeline
    time_slots = elements.get("T", [])
    if not time_slots:
        raise ValueError("No temperature data (T) found in CWB response")

    daily_forecast: list[dict] = []
    for slot in time_slots:
        start_time_str = slot.get("startTime", "")
        if not start_time_str:
            continue

        # Parse start_time to get date
        try:
            dt = datetime.fromisoformat(start_time_str)
        except ValueError:
            dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S%z")

        date_str = dt.strftime("%Y-%m-%d")
        weekday_map = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        weekday_str = weekday_map[dt.weekday()]

        # Check if this date is already in daily_forecast (for merging 12h slots)
        existing = next((d for d in daily_forecast if d["date"] == date_str), None)
        if existing is None:
            entry = {
                "location": loc_name,
                "date": date_str,
                "weekday": weekday_str,
                "wx": None,
                "pop": None,
                "max_t": None,
                "min_t": None,
                "max_at": None,
                "min_at": None,
                "rh": None,
                "ws": None,
                "wd": None,
                "uvi": None,
                "description": None,
                "start_time": start_time_str,
                "end_time": slot.get("endTime", ""),
            }
            daily_forecast.append(entry)
            existing = entry

        # Merge values from all elements for this time slot
        hour = dt.hour if dt.tzinfo else dt.hour
        is_day = 6 <= hour < 18  # roughly day vs night

        for ele_name, time_list in elements.items():
            for ts in time_list:
                if ts.get("startTime") == start_time_str:
                    val = _get_element_value(ts)
                    if val is None:
                        continue
                    _merge_element(existing, ele_name, val, is_day)

    return daily_forecast


def _get_element_value(ts: dict) -> Optional[str]:
    """Extract the measurement value from a time-slot dict."""
    values = ts.get("elementValue", [])
    if values and isinstance(values, list) and len(values) > 0:
        return values[0].get("value")
    return None


def _merge_element(entry: dict, ele_name: str, value: str, is_day: bool) -> None:
    """Merge a single element value into the daily forecast entry."""
    try:
        num_val = float(value)
    except (ValueError, TypeError):
        num_val = None

    if ele_name == "Wx":
        entry["wx"] = value
    elif ele_name == "PoP12h":
        entry["pop"] = num_val
    elif ele_name == "MaxT":
        entry["max_t"] = num_val
    elif ele_name == "MinT":
        entry["min_t"] = num_val
    elif ele_name == "MaxAT":
        entry["max_at"] = num_val
    elif ele_name == "MinAT":
        entry["min_at"] = num_val
    elif ele_name == "T":
        # Average temperature
        if entry["max_t"] is None and entry["min_t"] is None:
            val_int = round(num_val) if num_val is not None else None
            if is_day:
                entry["max_t"] = max(entry["max_t"] or 0, val_int or 0)
            else:
                entry["min_t"] = min(entry["min_t"] or 99, val_int or 99)
    elif ele_name == "RH":
        entry["rh"] = num_val
    elif ele_name == "WS":
        if num_val is not None:
            entry["ws"] = max(entry["ws"] or 0, num_val)
    elif ele_name == "WD":
        entry["wd"] = value
    elif ele_name == "UVI":
        if num_val is not None:
            entry["uvi"] = max(entry["uvi"] or 0, num_val)
    elif ele_name == "WeatherDescription":
        entry["description"] = value


# ─── Open-Meteo API (free, no API key) ────────────────────────────────────────

# Taiwan major cities' coordinates
CITY_COORDS = {
    "臺北市": (25.0330, 121.5654),
    "台北市": (25.0330, 121.5654),
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


def fetch_openmeteo_forecast(
    location_name: str,
    forecast_days: int = 7,
) -> dict:
    """Fetch weather forecast from Open-Meteo API (free, no API key).

    Args:
        location_name: City name (e.g. "臺北市", "高雄市").
        forecast_days: Number of days to forecast (max 16).

    Returns:
        Raw JSON response from Open-Meteo.

    Raises:
        ValueError: If location is not found.
    """
    coords = CITY_COORDS.get(location_name)
    if coords is None:
        # Try generic geocoding via Open-Meteo
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_params = {"name": location_name, "count": 1, "language": "zh", "format": "json"}
        geo_resp = requests.get(geo_url, params=geo_params, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
        results = geo_data.get("results", [])
        if not results:
            raise ValueError(f"Location not found: {location_name!r}")
        lat = results[0]["latitude"]
        lon = results[0]["longitude"]
    else:
        lat, lon = coords

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
        "forecast_days": forecast_days,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def parse_openmeteo_forecast(raw: dict, location_name: str) -> list[dict]:
    """Parse Open-Meteo response into daily forecast entries."""
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
        wx = WMO_WEATHER_CODES.get(code, f"未知 ({code})") if code is not None else None

        results.append({
            "location": location_name,
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
    """Convert wind direction degrees to Chinese direction."""
    directions = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"]
    index = round(degrees / 45) % 8
    return directions[index]


# ─── Unified interface ────────────────────────────────────────────────────────

DATA_SOURCES = {
    "cwb": (fetch_cwb_forecast, parse_cwb_forecast),
    "openmeteo": (fetch_openmeteo_forecast, parse_openmeteo_forecast),
}


def get_forecast(
    location_name: str,
    source: str = "openmeteo",
    api_key: Optional[str] = None,
) -> list[dict]:
    """Fetch and parse weather forecast from the specified data source.

    Args:
        location_name: City/district name.
        source: "cwb" (Taiwan CWB) or "openmeteo" (Open-Meteo, default).
        api_key: CWB API key (only needed for source="cwb").

    Returns:
        List of daily forecast dictionaries.
    """
    if source not in DATA_SOURCES:
        raise ValueError(f"Unknown data source: {source!r}. Use 'cwb' or 'openmeteo'.")

    fetch_fn, parse_fn = DATA_SOURCES[source]

    if source == "cwb":
        raw = fetch_fn(location_name, api_key=api_key)
    else:
        raw = fetch_fn(location_name)

    return parse_fn(raw, location_name) if source == "openmeteo" else parse_fn(raw)
