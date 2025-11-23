"""
Agent Configuration

Handles loading and managing agent configuration from YAML/JSON files
with environment variable overrides and feature flags.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.utils.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class AgentConfig:
    """
    Agent configuration manager.

    Loads configuration from YAML/JSON files and supports:
    - Environment variable overrides
    - Feature flags
    - Rate limiting configuration
    - Nested configuration values
    """

    def __init__(self, config_path: Optional[str] = None, agent_id: Optional[str] = None):
        """
        Initialize agent configuration.

        Args:
            config_path: Path to configuration file (YAML or JSON)
            agent_id: Optional agent ID for agent-specific config
        """
        self.agent_id = agent_id
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self._feature_flags: Dict[str, bool] = {}
        self._rate_limits: Dict[str, Dict[str, Any]] = {}

        if config_path:
            self.load_config(config_path)

    def load_config(self, config_path: str) -> None:
        """
        Load configuration from a file.

        Supports both YAML and JSON formats.

        Args:
            config_path: Path to configuration file

        Raises:
            ConfigurationError: If file cannot be loaded or parsed
        """
        path = Path(config_path)
        if not path.exists():
            raise ConfigurationError(
                config_key="config_path",
                details={"path": config_path, "reason": "File not found"},
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix.lower() in [".yaml", ".yml"]:
                    self._config = yaml.safe_load(f) or {}
                elif path.suffix.lower() == ".json":
                    self._config = json.load(f)
                else:
                    # Try YAML first, then JSON
                    try:
                        f.seek(0)
                        self._config = yaml.safe_load(f) or {}
                    except Exception:
                        f.seek(0)
                        self._config = json.load(f)

            # Apply environment variable overrides
            self._apply_env_overrides()

            # Extract feature flags and rate limits
            self._extract_feature_flags()
            self._extract_rate_limits()

            logger.info(f"Loaded configuration from {config_path}")

        except yaml.YAMLError as e:
            raise ConfigurationError(
                config_key="config_path",
                details={"path": config_path, "reason": f"YAML parse error: {e}"},
            ) from e
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                config_key="config_path",
                details={"path": config_path, "reason": f"JSON parse error: {e}"},
            ) from e
        except Exception as e:
            raise ConfigurationError(
                config_key="config_path",
                details={"path": config_path, "reason": str(e)},
            ) from e

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        # Environment variables follow the pattern: AGENT_<AGENT_ID>_<KEY> or AGENT_<KEY>
        prefix = f"AGENT_{self.agent_id.upper()}_" if self.agent_id else "AGENT_"

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to nested key
                config_key = key[len(prefix) :].lower()
                self._set_nested_value(config_key, value)

    def _set_nested_value(self, key: str, value: Any) -> None:
        """
        Set a nested configuration value.

        Supports dot notation (e.g., "database.host" -> {"database": {"host": value}}).

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split(".")
        config = self._config

        # Navigate to the parent dict
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the value, converting string booleans and numbers
        final_key = keys[-1]
        config[final_key] = self._convert_value(value)

    def _convert_value(self, value: str) -> Any:
        """
        Convert string value to appropriate type.

        Args:
            value: String value to convert

        Returns:
            Converted value (bool, int, float, or str)
        """
        # Try boolean
        if value.lower() in ("true", "1", "yes", "on"):
            return True
        if value.lower() in ("false", "0", "no", "off"):
            return False

        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Return as string
        return value

    def _extract_feature_flags(self) -> None:
        """Extract feature flags from configuration."""
        feature_flags = self.get("feature_flags", {})
        if isinstance(feature_flags, dict):
            self._feature_flags = {
                k: bool(v) for k, v in feature_flags.items()
            }
        else:
            self._feature_flags = {}

    def _extract_rate_limits(self) -> None:
        """Extract rate limiting configuration."""
        rate_limits = self.get("rate_limits", {})
        if isinstance(rate_limits, dict):
            self._rate_limits = rate_limits
        else:
            self._rate_limits = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Supports dot notation for nested values.

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_nested(self, *keys: str, default: Any = None) -> Any:
        """
        Get a nested configuration value using multiple keys.

        Args:
            *keys: Keys to navigate through nested structure
            default: Default value if path is not found

        Returns:
            Configuration value or default
        """
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Supports dot notation for nested values.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        self._set_nested_value(key, value)

    def has(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: Configuration key (supports dot notation)

        Returns:
            True if key exists, False otherwise
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return False

        return True

    def is_feature_enabled(self, feature: str) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            feature: Feature flag name

        Returns:
            True if feature is enabled, False otherwise
        """
        # Check environment variable first
        env_key = f"AGENT_{self.agent_id.upper()}_FEATURE_{feature.upper()}" if self.agent_id else f"AGENT_FEATURE_{feature.upper()}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return self._convert_value(env_value) is True

        # Check configuration
        return self._feature_flags.get(feature, False)

    def enable_feature(self, feature: str) -> None:
        """
        Enable a feature flag.

        Args:
            feature: Feature flag name
        """
        self._feature_flags[feature] = True
        if "feature_flags" not in self._config:
            self._config["feature_flags"] = {}
        self._config["feature_flags"][feature] = True

    def disable_feature(self, feature: str) -> None:
        """
        Disable a feature flag.

        Args:
            feature: Feature flag name
        """
        self._feature_flags[feature] = False
        if "feature_flags" not in self._config:
            self._config["feature_flags"] = {}
        self._config["feature_flags"][feature] = False

    def get_rate_limit(self, operation: str) -> Dict[str, Any]:
        """
        Get rate limiting configuration for an operation.

        Args:
            operation: Operation name

        Returns:
            Dictionary with rate limit configuration:
            - max_requests: Maximum number of requests
            - window_seconds: Time window in seconds
            - burst: Optional burst allowance
        """
        rate_limit = self._rate_limits.get(operation, {})
        return {
            "max_requests": rate_limit.get("max_requests", 100),
            "window_seconds": rate_limit.get("window_seconds", 60),
            "burst": rate_limit.get("burst", 10),
        }

    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire configuration dictionary.

        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()

    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.

        Args:
            updates: Dictionary of configuration updates
        """
        self._config.update(updates)
        self._extract_feature_flags()
        self._extract_rate_limits()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration as dictionary
        """
        return {
            "agent_id": self.agent_id,
            "config": self._config.copy(),
            "feature_flags": self._feature_flags.copy(),
            "rate_limits": self._rate_limits.copy(),
        }


def load_agent_config(agent_id: str, config_dir: Optional[str] = None) -> AgentConfig:
    """
    Load configuration for an agent.

    Looks for configuration files in the following order:
    1. <config_dir>/agents/<agent_id>.yaml
    2. <config_dir>/agents/<agent_id>.json
    3. <config_dir>/agents/<agent_id>/config.yaml
    4. <config_dir>/agents/<agent_id>/config.json

    Args:
        agent_id: ID of the agent
        config_dir: Optional configuration directory (defaults to project config dir)

    Returns:
        AgentConfig instance

    Raises:
        ConfigurationError: If no configuration file is found
    """
    if config_dir is None:
        # Default to project config directory
        config_dir = Path(__file__).parent.parent.parent / "config" / "agents"

    config_path = Path(config_dir)

    # Try different file locations
    possible_paths = [
        config_path / f"{agent_id}.yaml",
        config_path / f"{agent_id}.yml",
        config_path / f"{agent_id}.json",
        config_path / agent_id / "config.yaml",
        config_path / agent_id / "config.yml",
        config_path / agent_id / "config.json",
    ]

    for path in possible_paths:
        if path.exists():
            config = AgentConfig(config_path=str(path), agent_id=agent_id)
            logger.info(f"Loaded configuration for agent '{agent_id}' from {path}")
            return config

    # If no file found, create a default config
    logger.warning(f"No configuration file found for agent '{agent_id}', using defaults")
    return AgentConfig(agent_id=agent_id)



