#!/usr/bin/env python3
"""Main entry point for the weather Telegram notifier.

Reads ``config.yaml`` (or a custom path) and runs the notification pipeline.

Usage:
    python -m src.main
    python -m src.main --dry-run
    python -m src.main --config /path/to/config.yaml
    python -m src.main --location 高雄市
    python -m src.main --detail basic

Environment variables:
    CONFIG_PATH       - Path to config.yaml (default: ./config.yaml)
    TELEGRAM_BOT_TOKEN - Telegram Bot API token (fallback if not in config)
    TELEGRAM_CHAT_ID   - Target chat/group ID (fallback if not in config)
    CWB_API_KEY        - CWB API key (fallback if not in config)
"""

import argparse
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Weather forecast Telegram notifier",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config.yaml (overrides CONFIG_PATH env var)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the message to console without sending to Telegram",
    )
    parser.add_argument(
        "--location",
        default=None,
        help="Override city for all users (e.g. 高雄市)",
    )
    parser.add_argument(
        "--detail",
        default=None,
        choices=["basic", "standard", "full"],
        help="Override detail level for all users",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Load config, register implementations, and run the pipeline."""
    args = parse_args(argv)

    # Resolve config path: --config > CONFIG_PATH > ./config.yaml
    config_path = args.config or os.environ.get("CONFIG_PATH", "config.yaml")
    config_path = os.path.abspath(config_path)

    logger.info("Loading config from: %s", config_path)

    # Lazy imports to keep startup fast and avoid circular dependencies
    from .core.config import load_config
    from .core.pipeline import run_pipeline, register_source, register_notifier
    from .sources.openmeteo import OpenMeteoDataSource
    from .sources.cwb import CWBDataSource
    from .notifiers.telegram import TelegramNotifier

    # Register available implementations
    register_source("openmeteo", OpenMeteoDataSource)
    register_source("cwb", CWBDataSource)
    register_notifier("telegram", TelegramNotifier)

    # Load configuration
    config = load_config(config_path)

    if not config.users:
        logger.warning("No users found in config; nothing to do.")
        return 0

    # Run the pipeline
    exit_code = run_pipeline(
        config,
        dry_run=args.dry_run,
        override_location=args.location,
        override_detail=args.detail,
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
