"""Main pipeline orchestration.

For each user in config:
    1. Try data sources in priority order (failover: stop on first success).
    2. Format the forecast using ``formatter.format_forecast_message()``.
    3. Send the formatted message through each configured notifier.

If **all** sources fail for a user, an error notification is sent instead.
"""

import logging
from typing import Optional

from .config import Config, UserConfig
from ..formatter import format_forecast_message, format_error_message

logger = logging.getLogger(__name__)

# Global registries populated by main.py at startup
_source_registry: dict[str, type] = {}
_notifier_registry: dict[str, type] = {}


def register_source(name: str, cls: type) -> None:
    """Register a DataSource implementation class."""
    _source_registry[name] = cls


def register_notifier(name: str, cls: type) -> None:
    """Register a Notifier implementation class."""
    _notifier_registry[name] = cls


def run_pipeline(
    config: Config,
    dry_run: bool = False,
    override_location: Optional[str] = None,
    override_detail: Optional[str] = None,
) -> int:
    """Execute the full notification pipeline for all configured users.

    Args:
        config: Parsed configuration.
        dry_run: If True, print messages instead of sending.
        override_location: Override the city for all users (optional).
        override_detail: Override the detail level for all users (optional).

    Returns:
        0 if all users processed successfully, 1 if any errors occurred.
    """
    exit_code = 0

    for user in config.users:
        logger.info("Processing user: %s (city=%s)", user.name, user.city)

        location = override_location or user.city
        detail_level = override_detail or user.detail_level

        # ── 1. Try sources by ascending priority (failover) ──────────────
        sorted_sources = sorted(user.sources, key=lambda s: s.priority)
        forecast: Optional[list[dict]] = None
        source_name: Optional[str] = None
        last_error: Optional[str] = None

        for src_cfg in sorted_sources:
            source_cls = _source_registry.get(src_cfg.name)
            if source_cls is None:
                logger.warning(
                    "Unknown data source: %s (registered: %s)",
                    src_cfg.name,
                    list(_source_registry.keys()),
                )
                continue

            source = source_cls()
            logger.info(
                "Trying data source: %s (priority %d)",
                src_cfg.name,
                src_cfg.priority,
            )

            try:
                kwargs = {}
                if src_cfg.api_key:
                    kwargs["api_key"] = src_cfg.api_key

                raw = source.fetch(location, **kwargs)
                parsed = source.parse(raw, location)

                if parsed:
                    forecast = parsed
                    source_name = src_cfg.name
                    logger.info(
                        "Successfully fetched from %s (%d days)",
                        source_name,
                        len(forecast),
                    )
                    break

                last_error = f"{src_cfg.name}: returned empty forecast"
                logger.warning(last_error)

            except Exception as e:
                last_error = f"{src_cfg.name}: {e}"
                logger.warning("Source %s failed: %s", src_cfg.name, e)
                continue

        # ── 2. If all sources failed, send error notification ────────────
        if not forecast:
            error_msg = format_error_message(
                f"所有資料源皆無法取得天氣預報。\n最後錯誤：{last_error}"
            )
            logger.error("All sources failed for user %s: %s", user.name, last_error)
            _send_to_all_notifiers(user, error_msg, dry_run)
            exit_code = 1
            continue

        # ── 3. Generate chart (if enabled) ───────────────────────────────
        chart_path: str | None = None
        if user.charts:
            try:
                from ..charts.weather_chart import generate_weather_chart
                chart_path = generate_weather_chart(forecast, location)
                logger.info("Chart generated: %s", chart_path)
            except Exception as e:
                logger.error("Failed to generate chart: %s", e)

        # ── 4. Format the forecast message ───────────────────────────────
        message = format_forecast_message(
            forecast,
            location,
            source=source_name or "unknown",
            detail_level=detail_level,
        )
        logger.info("Formatted forecast message (%d chars)", len(message))

        # ── 5. Send to each notifier ─────────────────────────────────────
        _send_to_all_notifiers(user, message, dry_run, chart_path=chart_path)

    return exit_code


def _send_to_all_notifiers(
    user: UserConfig,
    message: str,
    dry_run: bool,
    chart_path: str | None = None,
) -> None:
    """Send *message* (and optionally a chart photo) through every notifier."""
    for notif_cfg in user.notifiers:
        notif_cls = _notifier_registry.get(notif_cfg.name)
        if notif_cls is None:
            logger.warning(
                "Unknown notifier: %s (registered: %s)",
                notif_cfg.name,
                list(_notifier_registry.keys()),
            )
            continue

        notifier = notif_cls()
        kwargs = {}
        if notif_cfg.bot_token:
            kwargs["bot_token"] = notif_cfg.bot_token
        if notif_cfg.chat_id:
            kwargs["chat_id"] = notif_cfg.chat_id
        if notif_cfg.message_thread_id is not None:
            kwargs["message_thread_id"] = notif_cfg.message_thread_id

        # Send chart photo first (if available)
        if chart_path and hasattr(notifier, "send_local_photo"):
            caption = f"🌤 {user.city} 未來 7 天天氣預報"
            if dry_run:
                logger.info(
                    "[DRY-RUN] Would send chart to user=%s via %s (path=%s)",
                    user.name, notif_cfg.name, chart_path,
                )
            else:
                try:
                    notifier.send_local_photo(chart_path, caption=caption, **kwargs)
                except Exception as e:
                    logger.error("Failed to send chart photo: %s", e)

        # Send text message
        if dry_run:
            logger.info(
                "[DRY-RUN] Would send to user=%s via %s",
                user.name,
                notif_cfg.name,
            )
            print(f"\n{'=' * 60}")
            print(f"DRY-RUN: User={user.name}, Notifier={notif_cfg.name}")
            print(f"{'=' * 60}")
            print(message)
        else:
            try:
                success = notifier.send(message, **kwargs)
                if success:
                    logger.info(
                        "Sent to user=%s via %s successfully",
                        user.name,
                        notif_cfg.name,
                    )
                else:
                    logger.error(
                        "Failed to send to user=%s via %s",
                        user.name,
                        notif_cfg.name,
                    )
            except Exception as e:
                logger.error(
                    "Error sending to user=%s via %s: %s",
                    user.name,
                    notif_cfg.name,
                    e,
                )
