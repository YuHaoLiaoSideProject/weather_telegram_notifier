"""Taiwan CWB (Central Weather Bureau) data source implementation.

Requires a registered API key from https://opendata.cwb.gov.tw/.
Only supports locations in Taiwan.
"""

import logging
import os
from datetime import datetime
from typing import Optional

import requests

from ..core.base import DataSource

logger = logging.getLogger(__name__)

CWB_API_BASE = "https://opendata.cwb.gov.tw/api/v1/rest/datastore"
# 鄉鎮天氣預報 - 台灣未來 1 週天氣預報
CWB_DATASET_ID = "F-D0047-091"

CWB_LOCATIONS = {
    "臺北市": "63",
    "台北市": "63",
    "新北市": "65",
    "桃園市": "68",
    "臺中市": "66",
    "台中市": "66",
    "臺南市": "67",
    "台南市": "67",
    "高雄市": "64",
    "基隆市": "69",
    "新竹市": "70",
    "新竹縣": "16",
    "苗栗縣": "13",
    "彰化縣": "07",
    "南投縣": "10",
    "雲林縣": "09",
    "嘉義市": "72",
    "嘉義縣": "20",
    "屏東縣": "14",
    "宜蘭縣": "17",
    "花蓮縣": "19",
    "臺東縣": "18",
    "台東縣": "18",
    "澎湖縣": "22",
    "金門縣": "30",
    "連江縣": "32",
}


class CWBDataSource(DataSource):
    """Weather data source using Taiwan CWB Open Data API.

    Requires an API key, provided either via the ``api_key`` kwarg
    or the ``CWB_API_KEY`` environment variable.
    """

    @property
    def name(self) -> str:
        return "cwb"

    def fetch(self, location: str, **kwargs) -> dict:
        api_key = kwargs.get("api_key") or os.environ.get("CWB_API_KEY")
        if not api_key:
            raise ValueError(
                "CWB API key is required. "
                "Set CWB_API_KEY environment variable or provide api_key in config."
            )

        geocode = CWB_LOCATIONS.get(location)
        if geocode is None:
            raise ValueError(
                f"Unknown location: {location!r}. "
                f"Available: {', '.join(sorted(set(k for k in CWB_LOCATIONS if len(k) == 3)))}"
            )

        url = f"{CWB_API_BASE}/{CWB_DATASET_ID}"
        params = {
            "Authorization": api_key,
            "locationName": location,
            "elementName": (
                "PoP12h,T,RH,MinCI,WS,MaxAT,Wx,MaxCI,"
                "MinT,UVI,WeatherDescription,MinAT,MaxT,WD,Td"
            ),
        }
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def parse(self, raw: dict, location: str) -> list[dict]:
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

        # Use temperature (T) slots as the reference timeline
        time_slots = elements.get("T", [])
        if not time_slots:
            raise ValueError("No temperature data (T) found in CWB response")

        daily_forecast: list[dict] = []
        for slot in time_slots:
            start_time_str = slot.get("startTime", "")
            if not start_time_str:
                continue

            try:
                dt = datetime.fromisoformat(start_time_str)
            except ValueError:
                dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S%z")

            date_str = dt.strftime("%Y-%m-%d")
            weekday_map = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
            weekday_str = weekday_map[dt.weekday()]

            # Merge 12h slots into daily entries
            existing = next(
                (d for d in daily_forecast if d["date"] == date_str), None
            )
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

            hour = dt.hour if dt.tzinfo else dt.hour
            is_day = 6 <= hour < 18

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
        # Average temperature — approximate max/min by day/night slot
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
