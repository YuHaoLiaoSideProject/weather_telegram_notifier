"""
Weather chart generator using Matplotlib.

Generates a card-style PNG image with:
  - Temperature line chart (max / min)
  - Rain probability bar chart
  - Weather icons / emoji labels
"""

import io
import logging
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates
logger = logging.getLogger(__name__)

# ── Font setup ────────────────────────────────────────────────────────────────

_CJK_FONT = None


def _get_cjk_font() -> str:
    """Find an installed CJK font by name priority."""
    global _CJK_FONT
    if _CJK_FONT:
        return _CJK_FONT

    for name in [
        "Noto Sans CJK TC",
        "Noto Sans CJK SC",
        "Noto Sans CJK",
        "WenQuanYi Micro Hei",
        "SimHei",
        "Microsoft YaHei",
    ]:
        try:
            font = fm.findfont(name, fallback_to_default=False)
            _CJK_FONT = font
            logger.info("Using CJK font: %s (%s)", name, font)
            return font
        except Exception:
            continue

    logger.warning("No CJK font found, falling back to default")
    return None


# ── Colour palette ────────────────────────────────────────────────────────────

CARD_BG = "#1a1a2e"
TEXT_COLOR = "#e0e0e0"
HIGHLIGHT = "#00d2ff"
MAX_TEMP_COLOR = "#ff6b6b"
MIN_TEMP_COLOR = "#4ecdc4"
POP_COLOR = "#74b9ff"
POP_ALPHA = 0.6
GRID_COLOR = "#334155"


def _parse_dates(forecast: list[dict]) -> list[datetime]:
    return [datetime.strptime(d["date"], "%Y-%m-%d") for d in forecast]


def generate_weather_chart(
    forecast: list[dict],
    location: str,
    output_path: str | None = None,
) -> str:
    """Generate a weather forecast chart image.

    Args:
        forecast: List of daily forecast dicts (from DataSource.parse).
        location: City/district name for the title.
        output_path: Where to save the PNG.  If None, uses a temp file.

    Returns:
        Absolute path to the generated PNG image.
    """
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".png", prefix="weather_")
        os.close(fd)

    dates = _parse_dates(forecast)
    max_temps = [d.get("max_t") or 0 for d in forecast]
    min_temps = [d.get("min_t") or 0 for d in forecast]
    pops = [d.get("pop") or 0 for d in forecast]
    wx_labels = [d.get("wx") or "" for d in forecast]

    font_path = _get_cjk_font()
    font_prop = fm.FontProperties(fname=font_path) if font_path else None
    font_kw = {"fontproperties": font_prop} if font_prop else {}

    # ── Figure ───────────────────────────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(
        2, 1,
        figsize=(10, 5.5),
        gridspec_kw={"height_ratios": [3, 1.2], "hspace": 0.35},
    )
    fig.patch.set_facecolor(CARD_BG)

    for ax in (ax1, ax2):
        ax.set_facecolor(CARD_BG)
        ax.tick_params(colors=TEXT_COLOR, labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color(GRID_COLOR)
        ax.spines["left"].set_color(GRID_COLOR)
        ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, linestyle="--")
        ax.set_xlim(dates[0], dates[-1])

    # ── Title ────────────────────────────────────────────────────────────
    now = datetime.now()
    title_str = f"{location}  ─  7 日天氣預報  ({now.month}/{now.day} 更新)"
    fig.suptitle(
        title_str,
        color=HIGHLIGHT,
        fontsize=13,
        fontweight="bold",
        y=0.98,
        **font_kw,
    )

    # ── Axes 1: Temperature lines ────────────────────────────────────────
    (line_max,) = ax1.plot(
        dates, max_temps,
        color=MAX_TEMP_COLOR, marker="o", linewidth=2.2, markersize=6,
        label="最高溫",
    )
    (line_min,) = ax1.plot(
        dates, min_temps,
        color=MIN_TEMP_COLOR, marker="s", linewidth=2.2, markersize=6,
        label="最低溫",
    )

    # Fill between
    ax1.fill_between(
        dates, min_temps, max_temps,
        color=MAX_TEMP_COLOR, alpha=0.08,
    )

    # Temperature labels above points
    for i, (d, t) in enumerate(zip(dates, max_temps)):
        ax1.annotate(
            f"{t:.0f}°",
            (d, t), textcoords="offset points", xytext=(0, 10),
            ha="center", fontsize=7.5, color=MAX_TEMP_COLOR,
            fontweight="bold", **font_kw,
        )
    for i, (d, t) in enumerate(zip(dates, min_temps)):
        ax1.annotate(
            f"{t:.0f}°",
            (d, t), textcoords="offset points", xytext=(0, -14),
            ha="center", fontsize=7.5, color=MIN_TEMP_COLOR,
            fontweight="bold", **font_kw,
        )

    # Weather text labels at top
    wx_short = [_short_wx(wx) for wx in wx_labels]
    for i, (d, label) in enumerate(zip(dates, wx_short)):
        ax1.annotate(
            label,
            (d, max_temps[i]), textcoords="offset points",
            xytext=(0, 24), ha="center", fontsize=7.5,
            color=TEXT_COLOR, fontweight="bold", **font_kw,
        )

    ax1.set_ylabel("溫度 (°C)", color=TEXT_COLOR, **font_kw)
    ax1.legend(
        loc="upper left", framealpha=0.7, facecolor=CARD_BG,
        edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR,
        prop=font_prop if font_prop else {"size": 8},
    )
    ax1.set_xticklabels([])

    # ── Axes 2: Rain probability bars ────────────────────────────────────
    color_list = []
    for p in pops:
        if p >= 70:
            color_list.append("#ef4444")   # red
        elif p >= 40:
            color_list.append("#f59e0b")   # amber
        else:
            color_list.append("#3b82f6")   # blue

    bars = ax2.bar(dates, pops, width=0.6, color=color_list, alpha=POP_ALPHA)

    for bar, p in zip(bars, pops):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.5,
            f"{p:.0f}%",
            ha="center", va="bottom", fontsize=7.5,
            color=TEXT_COLOR, fontweight="bold", **font_kw,
        )

    # Day-of-week labels
    weekday_map = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    tick_labels = []
    for d in dates:
        label = f"{d.month}/{d.day}\n{weekday_map[d.weekday()]}"
        tick_labels.append(label)
    ax2.set_xticks(dates)
    ax2.set_xticklabels(tick_labels, fontsize=7, color=TEXT_COLOR, **font_kw)

    ax2.set_ylabel("降雨機率 (%)", color=TEXT_COLOR, **font_kw)
    ax2.set_ylim(0, 110)

    # ── Footer ───────────────────────────────────────────────────────────
    fig.text(
        0.5, 0.01,
        "資料來源：Open-Meteo  |  每日自動更新",
        ha="center", fontsize=7, color="#64748b", **font_kw,
    )

    # ── Save ─────────────────────────────────────────────────────────────
    fig.savefig(output_path, dpi=180, bbox_inches="tight", facecolor=CARD_BG)
    plt.close(fig)
    logger.info("Chart saved to %s", output_path)

    return os.path.abspath(output_path)


def _short_wx(wx: str) -> str:
    """Shorten a weather description to 1-2 Chinese characters."""
    if not wx:
        return ""
    for kw, short in [
        ("雷暴", "雷雨"),
        ("冰雹", "冰雹"),
        ("大雪", "大雪"),
        ("小雪", "小雪"),
        ("大雨", "大雨"),
        ("毛毛雨", "小雨"),
        ("陣雨", "陣雨"),
        ("凍雨", "凍雨"),
        ("雨", "雨"),
        ("霧淞", "霧淞"),
        ("霧", "霧"),
        ("晴天", "晴"),
        ("晴朗", "晴"),
        ("多雲時晴", "晴時雲"),
        ("多雲", "多雲"),
        ("雪粒", "雪"),
        ("雪", "雪"),
    ]:
        if kw in wx:
            return short
    return "☁"  # fallback
