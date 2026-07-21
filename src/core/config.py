"""YAML configuration loader with environment variable substitution.

Supports ${ENV_VAR} syntax in config values, which are resolved
from the process environment at load time.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')


def _resolve_env_vars(value: Any) -> Any:
    """Recursively resolve ${ENV_VAR} patterns in a config value.

    Args:
        value: A string, dict, list, or scalar value from the YAML.

    Returns:
        The value with all environment variable references replaced.

    Raises:
        ValueError: If a referenced environment variable is not set.
    """
    if isinstance(value, str):
        def _replacer(match: re.Match) -> str:
            var_name = match.group(1)
            val = os.environ.get(var_name)
            if val is None:
                return ""
            return val
        return ENV_VAR_PATTERN.sub(_replacer, value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


@dataclass
class SourceConfig:
    """Configuration for a single data source."""
    name: str
    priority: int
    api_key: Optional[str] = None


@dataclass
class NotifierConfig:
    """Configuration for a single notifier."""
    name: str
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    message_thread_id: Optional[int] = None


@dataclass
class UserConfig:
    """Configuration for a single user / recipient."""
    name: str
    city: str
    detail_level: str = "full"
    sources: list[SourceConfig] = field(default_factory=list)
    notifiers: list[NotifierConfig] = field(default_factory=list)


@dataclass
class Config:
    """Top-level configuration."""
    users: list[UserConfig] = field(default_factory=list)


def load_config(config_path: Optional[str] = None) -> Config:
    """Load and parse the YAML configuration file.

    The config path is resolved in the following order:
        1. The *config_path* argument passed to this function.
        2. The ``CONFIG_PATH`` environment variable.
        3. ``./config.yaml`` (default).

    Any ``${ENV_VAR}`` patterns in string values are automatically
    resolved from the process environment.

    Args:
        config_path: Explicit path to the YAML config file.

    Returns:
        A :class:`Config` dataclass instance with all values resolved.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the config is malformed or an environment variable
            referenced in the file is missing.
    """
    if config_path is None:
        config_path = os.environ.get("CONFIG_PATH", "config.yaml")

    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raw = {}

    # Resolve all ${ENV_VAR} references
    resolved = _resolve_env_vars(raw)

    users_data = resolved.get("users", [])
    users: list[UserConfig] = []

    for u in users_data:
        sources = [
            SourceConfig(**s) for s in u.get("sources", [])
        ]
        notifiers = [
            NotifierConfig(**n) for n in u.get("notifiers", [])
        ]
        users.append(UserConfig(
            name=u.get("name", ""),
            city=u.get("city", "臺北市"),
            detail_level=u.get("detail_level", "full"),
            sources=sources,
            notifiers=notifiers,
        ))

    return Config(users=users)
