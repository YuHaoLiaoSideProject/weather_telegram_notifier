"""
Format weather forecast data into a human-readable message (Chinese).
"""

from datetime import datetime


TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]


def _emoji_for_temp(temp: float) -> str:
    if temp is None:
        return ""
    if temp >= 35:
        return "🥵"
    elif temp >= 30:
        return "🔥"
    elif temp >= 25:
        return "🌤"
    elif temp >= 20:
        return "😊"
    elif temp >= 15:
        return "🌥"
    elif temp >= 10:
        return "🧥"
    else:
        return "🥶"


def _weather_emoji(wx: str) -> str:
    """Extract emoji from weather description if it starts with one."""
    if wx and len(wx) > 0:
        # Already has emoji from Open-Meteo mapping
        return ""
    return ""


def _pop_emoji(pop) -> str:
    if pop is None:
        return ""
    if pop >= 70:
        return "🌧☂️"
    elif pop >= 40:
        return "🌦"
    elif pop >= 10:
        return "💧"
    return ""


def _uv_index_text(uvi) -> str:
    if uvi is None:
        return ""
    if uvi <= 2:
        return "低"
    elif uvi <= 5:
        return "中"
    elif uvi <= 7:
        return "高"
    elif uvi <= 10:
        return "極高"
    else:
        return "危險"


def _wind_level(ws) -> str:
    """Convert wind speed (m/s) to Beaufort scale roughly."""
    if ws is None:
        return ""
    if ws < 0.3:
        return "無風"
    elif ws < 1.6:
        return "微風"
    elif ws < 3.4:
        return "輕風"
    elif ws < 5.5:
        return "和風"
    elif ws < 8.0:
        return "強風"
    elif ws < 10.8:
        return "疾風"
    elif ws < 13.9:
        return "大風"
    else:
        return "烈風"


def _lunar_date() -> str:
    """Return a simple Chinese date string."""
    now = datetime.now()
    return now.strftime("%Y 年 %m 月 %d 日")


def format_daily_forecast(day: dict, detail_level: str = "full") -> str:
    """Format a single day's forecast into a compact text block.

    Args:
        day: Single day forecast dict.
        detail_level: "basic", "standard", or "full".
            basic    - weather icon + temperature + rain probability
            standard - basic + apparent temp + humidity + wind
            full     - standard + UV index + description
    """
    date_str = day["date"]
    weekday = day["weekday"]
    wx = day["wx"] or ""
    pop = day.get("pop")
    max_t = day.get("max_t")
    min_t = day.get("min_t")
    max_at = day.get("max_at")
    min_at = day.get("min_at")
    rh = day.get("rh")
    ws = day.get("ws")
    wd = day.get("wd")
    uvi = day.get("uvi")
    desc = day.get("description")

    lines = [f"📅 {date_str} ({weekday})"]

    # Weather phenomenon
    if wx:
        lines.append(f"   ☁️ 天氣：{wx}")

    # Temperature
    temp_parts = []
    if max_t is not None:
        temp_parts.append(f"最高 {max_t:.0f}°C")
    if min_t is not None:
        temp_parts.append(f"最低 {min_t:.0f}°C")
    if temp_parts:
        emoji = _emoji_for_temp(max_t if max_t is not None else min_t)
        lines.append(f"   🌡 溫度：{' / '.join(temp_parts)} {emoji}")

    # Apparent temperature (standard+)
    if detail_level in ("standard", "full"):
        at_parts = []
        if max_at is not None:
            at_parts.append(f"最高體感 {max_at:.0f}°C")
        if min_at is not None:
            at_parts.append(f"最低體感 {min_at:.0f}°C")
        if at_parts:
            lines.append(f"   🌡 體感：{' / '.join(at_parts)}")

    # Rain probability
    if pop is not None:
        pop_line = f"   {_pop_emoji(pop)} 降雨機率：{pop:.0f}%"
        if detail_level == "basic" and pop < 30:
            pass  # skip low probability in basic mode
        else:
            lines.append(pop_line)

    # Humidity (standard+)
    if detail_level in ("standard", "full") and rh is not None:
        lines.append(f"   💧 濕度：{rh:.0f}%")

    # Wind (standard+)
    if detail_level in ("standard", "full"):
        wind_parts = []
        if wd:
            wind_parts.append(wd)
        if ws is not None:
            wind_parts.append(f"{ws:.1f} m/s")
            wind_parts.append(f"({_wind_level(ws)})")
        if wind_parts:
            lines.append(f"   💨 風速：{' '.join(wind_parts)}")



    # UV index (full only)
    if detail_level == "full" and uvi is not None:
        lines.append(f"   ☀️ 紫外線：{uvi:.0f}（{_uv_index_text(uvi)}）")

    # Full description - full only (CWB)
    if detail_level == "full" and desc:
        lines.append(f"   📝 {desc}")

    return "\n".join(lines)


def format_forecast_message(
    forecast: list[dict],
    location: str,
    source: str = "openmeteo",
    detail_level: str = "full",
) -> str:
    """Format the full weather forecast message for Telegram.

    Args:
        forecast: List of daily forecast dicts.
        location: City name.
        source: Data source name.
        detail_level: "basic", "standard", or "full".

    Returns:
        Formatted multi-line message string.
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    weekday_map = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    now_weekday = weekday_map[now.weekday()]
    time_str = now.strftime("%H:%M")

    # Title
    lines = [
        f"🌤 **天氣預報通知**",
        f"",
        f"📍 {location}  |  🕐 {today_str} ({now_weekday}) {time_str}",
        f"",
    ]

    # Detail level tag
    level_labels = {"basic": "精簡", "standard": "標準", "full": "完整"}
    lines.append(f"📊 詳細程度：{level_labels.get(detail_level, detail_level)}")
    lines.append("")

    # Source note
    if source == "openmeteo":
        lines.append(f"📡 資料來源：Open-Meteo (免費開放資料)")
    else:
        lines.append(f"📡 資料來源：中央氣象署 CWB")
    lines.append("")

    # Separator
    lines.append("━" * 28)

    # Each day
    for day in forecast:
        lines.append("")
        lines.append(format_daily_forecast(day, detail_level=detail_level))

    # Summary footer
    lines.append("")
    lines.append("━" * 28)
    lines.append("")
    lines.append("🤖 由 GitHub Actions 自動發送 · 每日更新")

    return "\n".join(lines)


def format_error_message(error_msg: str) -> str:
    """Format an error message for Telegram notification."""
    return (
        f"⚠️ **天氣預報擷取失敗**\n\n"
        f"無法取得天氣資料：\n{error_msg}\n\n"
        f"請檢查 API 設定或網路連線。"
    )
