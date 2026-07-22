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

    def send_local_photo(
        self,
        photo_path: str,
        caption: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """Send a local image file as a photo via Telegram Bot API.

        Uses multipart/form-data upload.

        Args:
            photo_path: Absolute path to the local image file.
            caption: Optional caption (Markdown, ≤1024 chars).
            **kwargs: May contain ``bot_token``, ``chat_id``, ``message_thread_id``.

        Returns:
            True if the photo was accepted by the Telegram API.
        """
        bot_token = kwargs.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = kwargs.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID")
        thread_id = kwargs.get("message_thread_id")

        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN is not set")
            return False
        if not chat_id:
            logger.error("TELEGRAM_CHAT_ID is not set")
            return False

        url = f"{TELEGRAM_API_BASE}{bot_token}/sendPhoto"

        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
                data["parse_mode"] = "Markdown"
            if thread_id is not None:
                data["message_thread_id"] = thread_id

            try:
                resp = requests.post(url, files=files, data=data, timeout=30)
                resp.raise_for_status()
                result = resp.json()
                if result.get("ok"):
                    logger.info("Photo sent successfully")
                    return True
                logger.error("Telegram API error: %s", result)
                return False
            except requests.RequestException as e:
                logger.error("Failed to send photo: %s", e)
                return False
