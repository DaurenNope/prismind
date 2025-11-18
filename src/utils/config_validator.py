#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Configuration Validator for BEYONDLINES
=====================================

Validates configuration with schema validation, type checking, and value constraints.
Prevents configuration errors early with clear error messages.

Author: BEYONDLINES AI System
"""

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from src.utils.logging_config import get_logger


class ValidationError(Exception):
    """Configuration validation error"""

    pass


class ConfigValueType(Enum):
    """Types of configuration values"""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    PATH = "path"
    URL = "url"
    EMAIL = "email"


@dataclass
class ConfigField:
    """Definition of a configuration field"""

    name: str
    value_type: ConfigValueType
    required: bool = True
    default: Any = None
    description: str = ""
    validator: Optional[Callable[[Any], bool]] = None
    allowed_values: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern for strings


@dataclass
class ValidationResult:
    """Result of configuration validation"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validated_config: Optional[Dict[str, Any]] = None

    def __bool__(self):
        return self.is_valid


class ConfigValidator:
    """
    Validates configuration against a schema.

    Usage:
        validator = ConfigValidator()
        validator.add_field("database_url", ConfigValueType.URL, required=True)
        validator.add_field("max_connections", ConfigValueType.INTEGER, min_value=1, max_value=100)

        result = validator.validate(config_dict)
        if not result:
            for error in result.errors:
                logger.error(error)
    """

    def __init__(self):
        self.fields: Dict[str, ConfigField] = {}
        self.logger = get_logger(__name__)

    def add_field(
        self,
        name: str,
        value_type: ConfigValueType,
        required: bool = True,
        default: Any = None,
        description: str = "",
        validator: Optional[Callable[[Any], bool]] = None,
        allowed_values: Optional[List[Any]] = None,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
    ):
        """Add a field to the schema"""
        field = ConfigField(
            name=name,
            value_type=value_type,
            required=required,
            default=default,
            description=description,
            validator=validator,
            allowed_values=allowed_values,
            min_value=min_value,
            max_value=max_value,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
        )
        self.fields[name] = field

    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration against schema"""
        errors: List[str] = []
        warnings: List[str] = []
        validated_config: Dict[str, Any] = {}

        # Check for required fields
        for field_name, field in self.fields.items():
            if field.required and field_name not in config:
                if field.default is not None:
                    validated_config[field_name] = field.default
                    warnings.append(
                        f"Missing required field '{field_name}', using default: {field.default}"
                    )
                else:
                    errors.append(
                        f"Missing required field: '{field_name}' ({field.description or 'no description'})"
                    )
                    continue

        # Validate each field
        for field_name, value in config.items():
            if field_name not in self.fields:
                warnings.append(
                    f"Unknown configuration field: '{field_name}' (will be ignored)"
                )
                continue

            field = self.fields[field_name]
            validation_error = self._validate_field(field, value)
            if validation_error:
                errors.append(f"Field '{field_name}': {validation_error}")
            else:
                validated_config[field_name] = value

        # Apply defaults for missing optional fields
        for field_name, field in self.fields.items():
            if field_name not in validated_config and field.default is not None:
                validated_config[field_name] = field.default

        is_valid = len(errors) == 0
        result = ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_config=validated_config if is_valid else None,
        )

        if not is_valid:
            self.logger.error(
                f"Configuration validation failed: {len(errors)} error(s), {len(warnings)} warning(s)"
            )
            for error in errors:
                self.logger.error(f"  - {error}")

        if warnings:
            self.logger.warning(
                f"Configuration validation warnings: {len(warnings)} warning(s)"
            )
            for warning in warnings:
                self.logger.warning(f"  - {warning}")

        return result

    def _validate_field(self, field: ConfigField, value: Any) -> Optional[str]:
        """Validate a single field value"""
        # Type checking
        type_error = self._check_type(field.value_type, value)
        if type_error:
            return type_error

        # Allowed values check
        if field.allowed_values is not None and value not in field.allowed_values:
            return f"Value must be one of: {field.allowed_values}, got: {value}"

        # Range checks for numbers
        if field.value_type in (ConfigValueType.INTEGER, ConfigValueType.FLOAT):
            if field.min_value is not None and value < field.min_value:
                return f"Value must be >= {field.min_value}, got: {value}"
            if field.max_value is not None and value > field.max_value:
                return f"Value must be <= {field.max_value}, got: {value}"

        # Length checks for strings and lists
        if field.value_type == ConfigValueType.STRING:
            str_value = str(value)
            if field.min_length is not None and len(str_value) < field.min_length:
                return f"String length must be >= {field.min_length}, got: {len(str_value)}"
            if field.max_length is not None and len(str_value) > field.max_length:
                return f"String length must be <= {field.max_length}, got: {len(str_value)}"
            if field.pattern:
                import re

                if not re.match(field.pattern, str_value):
                    return f"String must match pattern: {field.pattern}"

        if field.value_type == ConfigValueType.LIST:
            if field.min_length is not None and len(value) < field.min_length:
                return f"List length must be >= {field.min_length}, got: {len(value)}"
            if field.max_length is not None and len(value) > field.max_length:
                return f"List length must be <= {field.max_length}, got: {len(value)}"

        # URL validation
        if field.value_type == ConfigValueType.URL:
            if not self._is_valid_url(value):
                return f"Invalid URL: {value}"

        # Email validation
        if field.value_type == ConfigValueType.EMAIL:
            if not self._is_valid_email(value):
                return f"Invalid email: {value}"

        # Path validation
        if field.value_type == ConfigValueType.PATH:
            path = Path(value)
            if field.required and not path.exists():
                return f"Path does not exist: {value}"

        # Custom validator
        if field.validator and not field.validator(value):
            return f"Custom validation failed for value: {value}"

        return None

    def _check_type(self, value_type: ConfigValueType, value: Any) -> Optional[str]:
        """Check if value matches expected type"""
        if value_type == ConfigValueType.STRING:
            if not isinstance(value, str):
                return f"Expected string, got {type(value).__name__}"
        elif value_type == ConfigValueType.INTEGER:
            if not isinstance(value, int):
                return f"Expected integer, got {type(value).__name__}"
        elif value_type == ConfigValueType.FLOAT:
            if not isinstance(value, (int, float)):
                return f"Expected float, got {type(value).__name__}"
        elif value_type == ConfigValueType.BOOLEAN:
            if not isinstance(value, bool):
                return f"Expected boolean, got {type(value).__name__}"
        elif value_type == ConfigValueType.LIST:
            if not isinstance(value, list):
                return f"Expected list, got {type(value).__name__}"
        elif value_type == ConfigValueType.DICT:
            if not isinstance(value, dict):
                return f"Expected dict, got {type(value).__name__}"
        elif value_type == ConfigValueType.PATH:
            if not isinstance(value, (str, Path)):
                return f"Expected path (string or Path), got {type(value).__name__}"
        elif value_type == ConfigValueType.URL:
            if not isinstance(value, str):
                return f"Expected URL (string), got {type(value).__name__}"
        elif value_type == ConfigValueType.EMAIL:
            if not isinstance(value, str):
                return f"Expected email (string), got {type(value).__name__}"

        return None

    def _is_valid_url(self, value: str) -> bool:
        """Check if string is a valid URL"""
        try:
            from urllib.parse import urlparse

            result = urlparse(value)
            return all([result.scheme, result.netloc])
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    def _is_valid_email(self, value: str) -> bool:
        """Check if string is a valid email"""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, value))


def create_beyondlines_config_validator() -> ConfigValidator:
    """Create a validator with BEYONDLINES-specific configuration schema"""
    validator = ConfigValidator()

    # Supabase configuration
    validator.add_field(
        "supabase_url",
        ConfigValueType.URL,
        required=True,
        description="Supabase project URL",
    )
    validator.add_field(
        "supabase_service_role_key",
        ConfigValueType.STRING,
        required=True,
        min_length=20,
        description="Supabase service role key",
    )

    # Feature flags
    validator.add_field(
        "supabase_enabled",
        ConfigValueType.BOOLEAN,
        required=False,
        default=True,
        description="Enable Supabase integration",
    )
    validator.add_field(
        "enable_sqlite_cache",
        ConfigValueType.BOOLEAN,
        required=False,
        default=False,
        description="Enable SQLite cache",
    )
    validator.add_field(
        "enable_analysis",
        ConfigValueType.BOOLEAN,
        required=False,
        default=True,
        description="Enable AI analysis",
    )
    validator.add_field(
        "enable_threads",
        ConfigValueType.BOOLEAN,
        required=False,
        default=False,
        description="Enable Threads collection",
    )

    # Performance settings
    validator.add_field(
        "auto_pipeline_batch_limit",
        ConfigValueType.INTEGER,
        required=False,
        default=25,
        min_value=1,
        max_value=1000,
        description="Batch size for pipeline operations",
    )

    # Rewriter settings
    validator.add_field(
        "rewriter_min_quality_score",
        ConfigValueType.FLOAT,
        required=False,
        default=5.0,
        min_value=0.0,
        max_value=10.0,
        description="Minimum quality score for rewriting",
    )

    return validator


def validate_config(
    config: Dict[str, Any], schema: Optional[ConfigValidator] = None
) -> ValidationResult:
    """Validate configuration with default BEYONDLINES schema"""
    if schema is None:
        schema = create_beyondlines_config_validator()
    return schema.validate(config)
