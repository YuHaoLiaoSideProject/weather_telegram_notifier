"""
Format weather forecast data into a compact human-readable message (Chinese).
"""

from datetime import datetime


def _temp_emoji(max_t: float | None) -> str:
    if max_t is None:
        return ""
    if max_t >= 35:
        return "🥵"
    elif max_t >= 30:
        return "🔥"
    elif max_t >= 25:
        return "🌤"
    elif max_t >= 20:
        return "😊"
    elif max_t >= 15:
        return "🌥"
    else:
        return "🥶"


def _pop_label(pop: float | None) -> str:
    """Return a short rain-probability string.
    Only shown when odds are meaningful (>= 30%).
    """
    if pop is None:
        return ""
    if pop >= 60:
        return f"  🌧{pop:.0f}%"   # likely rain
    elif pop >= 30:
        return f"  🌦{pop:.0f}%"   # possible rain
    return ""                         # low chance, skip


def _extract_emoji(wx: str) -> str:
    """Extract leading emoji from wx string, e.g. '☀️ 晴天' → '☀️'.
    Handles multi-codepoint emoji (emoji + U+FE0F variation selector).
    """
    if not wx:
        return ""
    result = ""
    for ch in wx:
        cp = ord(ch)
        if cp == 0xFE0F:  # variation selector-16 (makes emoji style)
            result += ch
        elif cp > 0x2000:
            if not result:  # first emoji char
                result = ch
            else:
                break  # second emoji = stop
        else:
            if result:
                break  # non-emoji after emoji = stop
    return result


def format_forecast_message(
    forecast: list[dict],
    location: str,
    source: str = "openmeteo",
    detail_level: str = "basic",
) -> str:
    """Format a very compact 7-day forecast message.

    Args:
        forecast: List of daily forecast dicts.
        location: City name.
        source: Data source name (ignored in compact mode).
        detail_level: "basic", "standard", or "full" — currently all produce
                      the same compact output.

    Returns:
        A short multi-line message ready for Telegram.
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    lines = [
        f"🌤 **{location} — 未來 7 天天氣**",
        f"📅 {today_str}  每日更新",
        "",
        "```",
    ]

    # Compact table: day  date   wx   temp        rain
    #               週三  07/23  ☀️  26~34°C 🔥   💧10%
    for day in forecast:
        dt = datetime.strptime(day["date"], "%Y-%m-%d")
        md = dt.strftime("%m/%d")
        wd = day["weekday"]
        wx = day.get("wx") or ""
        max_t = day.get("max_t")
        min_t = day.get("min_t")
        pop = day.get("pop")

        emoji = _extract_emoji(wx)

        # Temperature range
        if max_t is not None and min_t is not None:
            temp_str = f"{min_t:.0f}~{max_t:.0f}°C"
        elif max_t is not None:
            temp_str = f"{max_t:.0f}°C"
        elif min_t is not None:
            temp_str = f"{min_t:.0f}°C"
        else:
            temp_str = "--"

        temp_emoji = _temp_emoji(max_t)

        # Rain probability (only when >= 30%)
        rain_str = _pop_label(pop)

        lines.append(
            f"{wd} {md}  {emoji}  {temp_str} {temp_emoji}{rain_str}"
        )

    lines.append("```")
    lines.append("")
    lines.append("🤖 自動發送 · 每日更新")

    return "\n".join(lines)


def format_error_message(error_msg: str) -> str:
    """Format an error message for Telegram notification."""
    return (
        f"⚠️ **天氣預報擷取失敗**\n\n"
        f"無法取得天氣資料：\n{error_msg}\n\n"
        f"請檢查 API 設定或網路連線。"
    )
