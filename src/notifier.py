"""
Telegram notification module.
Sends messages via Telegram Bot API using HTTP requests (no extra library needed).
"""

import os
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


def send_telegram_message(
    message: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
    parse_mode: str = "Markdown",
) -> bool:
    """Send a message via Telegram Bot API.

    Args:
        message: The text message to send.
        bot_token: Telegram Bot API token. Falls back to TELEGRAM_BOT_TOKEN env var.
        chat_id: Target chat ID. Falls back to TELEGRAM_CHAT_ID env var.
        parse_mode: "Markdown" or "HTML" formatting.

    Returns:
        True if sent successfully, False otherwise.
    """
    if bot_token is None:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if chat_id is None:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set")
        return False
    if not chat_id:
        logger.error("TELEGRAM_CHAT_ID is not set")
        return False

    url = f"{TELEGRAM_API_BASE}{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        result = resp.json()
        if result.get("ok"):
            logger.info("Telegram message sent successfully")
            return True
        else:
            logger.error(f"Telegram API error: {result}")
            return False
    except requests.RequestException as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def send_telegram_photo(
    photo_url: str,
    caption: Optional[str] = None,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> bool:
    """Send a photo via Telegram Bot API.

    Args:
        photo_url: URL of the image to send.
        caption: Optional caption for the photo.
        bot_token: Telegram Bot API token.
        chat_id: Target chat ID.

    Returns:
        True if sent successfully.
    """
    if bot_token is None:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if chat_id is None:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False

    url = f"{TELEGRAM_API_BASE}{bot_token}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "parse_mode": "Markdown",
    }
    if caption:
        payload["caption"] = caption

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json().get("ok", False)
    except requests.RequestException as e:
        logger.error(f"Failed to send photo: {e}")
        return False
