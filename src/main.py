"""
Main entry point for the weather Telegram notifier.

Usage:
    python -m src.main                          # Uses env vars
    python -m src.main --location 臺北市
    python -m src.main --source cwb             # Use Taiwan CWB API (needs CWB_API_KEY)
    python -m src.main --source openmeteo       # Use Open-Meteo (default, no API key)
    python -m src.main --detail basic           # 精簡模式
    python -m src.main --detail standard        # 標準模式
    python -m src.main --detail full            # 完整模式 (預設)

Environment variables:
    TELEGRAM_BOT_TOKEN   - Telegram Bot API token (required)
    TELEGRAM_CHAT_ID     - Target chat/group ID (required)
    CWB_API_KEY          - CWB API key (only needed for source=cwb)
    WEATHER_LOCATION     - City name (default: 臺北市)
    WEATHER_SOURCE       - Data source: cwb or openmeteo (default: openmeteo)
    DETAIL_LEVEL         - basic / standard / full (default: full)
"""

import argparse
import logging
import os
import sys

from .weather import get_forecast
from .formatter import format_forecast_message, format_error_message
from .notifier import send_telegram_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Weather forecast Telegram notifier",
    )
    parser.add_argument(
        "--location",
        default=os.environ.get("WEATHER_LOCATION", "臺北市"),
        help="City/district name (default: WEATHER_LOCATION env or 臺北市)",
    )
    parser.add_argument(
        "--source",
        default=os.environ.get("WEATHER_SOURCE", "openmeteo"),
        choices=["cwb", "openmeteo"],
        help="Data source: cwb (Taiwan CWB) or openmeteo (default: openmeteo)",
    )
    parser.add_argument(
        "--detail",
        default=os.environ.get("DETAIL_LEVEL", "full"),
        choices=["basic", "standard", "full"],
        help="Detail level: basic (精簡), standard (標準), full (完整, default)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the message to console without sending to Telegram",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    logger.info(
        "Starting weather forecast notifier: location=%s source=%s",
        args.location,
        args.source,
    )

    # Fetch forecast
    try:
        forecast = get_forecast(
            location_name=args.location,
            source=args.source,
        )
    except Exception as e:
        error_msg = format_error_message(str(e))
        logger.error("Failed to fetch weather data: %s", e)
        if args.dry_run:
            print(error_msg)
        else:
            send_telegram_message(error_msg)
        return 1

    if not forecast:
        error_msg = format_error_message("No forecast data returned.")
        logger.error("No forecast data returned")
        if args.dry_run:
            print(error_msg)
        else:
            send_telegram_message(error_msg)
        return 1

    # Format message
    message = format_forecast_message(forecast, args.location, args.source, detail_level=args.detail)
    logger.info("Formatted forecast message (%d chars)", len(message))

    # Send or dry-run
    if args.dry_run:
        print(message)
    else:
        success = send_telegram_message(message)
        if success:
            logger.info("Notification sent successfully")
        else:
            logger.error("Failed to send notification")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
