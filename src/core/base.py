"""Abstract base classes for data sources and notifiers.

Defines the interfaces that all data sources and notification
channels must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class DataSource(ABC):
    """Abstract base class for weather data sources.

    Subclasses must implement:
        - name property
        - fetch(location, **kwargs) -> dict
        - parse(raw, location) -> list[dict]
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the data source identifier (e.g. 'openmeteo', 'cwb')."""
        ...

    @abstractmethod
    def fetch(self, location: str, **kwargs: Any) -> dict:
        """Fetch raw weather data for the given location.

        Args:
            location: City/district name (e.g. '臺北市').
            **kwargs: Source-specific parameters (e.g. api_key).

        Returns:
            Raw JSON-like dict from the API.

        Raises:
            Exception: On network errors, missing API keys, or unknown locations.
        """
        ...

    @abstractmethod
    def parse(self, raw: dict, location: str) -> list[dict]:
        """Parse raw API response into a list of daily forecast entries.

        Each entry dict should contain at minimum:
            date, weekday, location, wx, pop, max_t, min_t, ...

        Args:
            raw: The raw data dict returned by fetch().
            location: City/district name (for reference).

        Returns:
            List of daily forecast dicts.

        Raises:
            ValueError: If the response format is unexpected or missing data.
        """
        ...


class Notifier(ABC):
    """Abstract base class for notification channels.

    Subclasses must implement:
        - name property
        - send(message, **kwargs) -> bool
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the notifier identifier (e.g. 'telegram')."""
        ...

    @abstractmethod
    def send(self, message: str, **kwargs: Any) -> bool:
        """Send a notification message.

        Args:
            message: The formatted message text to send.
            **kwargs: Notifier-specific parameters (e.g. bot_token, chat_id).

        Returns:
            True if the message was sent successfully, False otherwise.
        """
        ...
