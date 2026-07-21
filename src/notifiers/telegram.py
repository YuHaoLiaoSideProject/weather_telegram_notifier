"""Telegram notifier implementation.

Sends messages via the Telegram Bot API using HTTP requests
(no extra library beyond ``requests``).
"""

import logging
import os
from typing import Optional

import requests

from ..core.base import Notifier

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


class TelegramNotifier(Notifier):
    """Send notifications via Telegram Bot API.

    Credentials are resolved from (in order):
        1. The ``bot_token`` / ``chat_id`` kwargs passed to :meth:`send`.
        2. The ``TELEGRAM_BOT_TOKEN`` / ``TELEGRAM_CHAT_ID`` environment variables.
    """

    @property
    def name(self) -> str:
        return "telegram"

    def send(self, message: str, **kwargs) -> bool:
        """Send a text message to a Telegram chat.

        Args:
            message: The message text (Markdown-formatted).
            **kwargs: May contain ``bot_token`` and ``chat_id``.

        Returns:
            True if the message was accepted by the Telegram API.
        """
        bot_token = kwargs.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = kwargs.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID")

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
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        # Forum topic support (message_thread_id)
        thread_id = kwargs.get("message_thread_id")
        if thread_id is not None:
            payload["message_thread_id"] = thread_id

        try:
            resp = requests.post(url, json=payload, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            if result.get("ok"):
                logger.info("Telegram message sent successfully")
                return True
            logger.error("Telegram API error: %s", result)
            return False
        except requests.RequestException as e:
            logger.error("Failed to send Telegram message: %s", e)
            return False

    def send_photo(
        self,
        photo_url: str,
        caption: Optional[str] = None,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> bool:
        """Send a photo via Telegram Bot API.

        Reserved for Phase 2 (chart attachments).

        Args:
            photo_url: Public URL of the image to send.
            caption: Optional caption for the photo.
            bot_token: Override bot token.
            chat_id: Override chat ID.

        Returns:
            True if the photo was accepted by the Telegram API.
        """
        if bot_token is None:
            bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if chat_id is None:
            chat_id = os.environ.get("TELEGRAM_CHAT_ID")

        if not bot_token or not chat_id:
            logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
            return False

        url = f"{TELEGRAM_API_BASE}{bot_token}/sendPhoto"
        payload: dict = {
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
            logger.error("Failed to send photo: %s", e)
            return False
