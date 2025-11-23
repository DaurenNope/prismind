#!/usr/bin/env python3
"""
Input Validation Middleware for BEYONDLINES
Provides centralized validation for all user inputs and API parameters.
"""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class InputValidator:
    """
    Centralized input validation with common validation rules.
    """

    @staticmethod
    def validate_string(
        value: Any,
        name: str = "field",
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        required: bool = True,
        allow_none: bool = False,
    ) -> str:
        """
        Validate a string value.
        
        Args:
            value: Value to validate
            name: Field name for error messages
            min_length: Minimum length (optional)
            max_length: Maximum length (optional)
            pattern: Regex pattern to match (optional)
            required: Whether field is required
            allow_none: Whether None is allowed
            
        Returns:
            Validated string value
            
        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if allow_none:
                return None
            if not required:
                return ""
            raise ValidationError(f"{name} is required")
        
        value_str = str(value).strip()
        
        if not value_str and required:
            raise ValidationError(f"{name} cannot be empty")
        
        if min_length is not None and len(value_str) < min_length:
            raise ValidationError(
                f"{name} must be at least {min_length} characters long"
            )
        
        if max_length is not None and len(value_str) > max_length:
            raise ValidationError(
                f"{name} must be at most {max_length} characters long"
            )
        
        if pattern and not re.match(pattern, value_str):
            raise ValidationError(f"{name} does not match required format")
        
        return value_str

    @staticmethod
    def validate_int(
        value: Any,
        name: str = "field",
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        required: bool = True,
        allow_none: bool = False,
    ) -> Optional[int]:
        """Validate an integer value."""
        if value is None:
            if allow_none:
                return None
            if not required:
                return None
            raise ValidationError(f"{name} is required")
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{name} must be a valid integer")
        
        if min_value is not None and int_value < min_value:
            raise ValidationError(f"{name} must be at least {min_value}")
        
        if max_value is not None and int_value > max_value:
            raise ValidationError(f"{name} must be at most {max_value}")
        
        return int_value

    @staticmethod
    def validate_float(
        value: Any,
        name: str = "field",
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        required: bool = True,
        allow_none: bool = False,
    ) -> Optional[float]:
        """Validate a float value."""
        if value is None:
            if allow_none:
                return None
            if not required:
                return None
            raise ValidationError(f"{name} is required")
        
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{name} must be a valid number")
        
        if min_value is not None and float_value < min_value:
            raise ValidationError(f"{name} must be at least {min_value}")
        
        if max_value is not None and float_value > max_value:
            raise ValidationError(f"{name} must be at most {max_value}")
        
        return float_value

    @staticmethod
    def validate_enum(
        value: Any,
        name: str = "field",
        allowed_values: List[str] = None,
        required: bool = True,
        allow_none: bool = False,
    ) -> Optional[str]:
        """Validate an enum value."""
        if allowed_values is None:
            allowed_values = []
        
        if value is None:
            if allow_none:
                return None
            if not required:
                return None
            raise ValidationError(f"{name} is required")
        
        value_str = str(value).strip()
        
        if value_str not in allowed_values:
            raise ValidationError(
                f"{name} must be one of: {', '.join(allowed_values)}"
            )
        
        return value_str

    @staticmethod
    def validate_url(
        value: Any,
        name: str = "url",
        required: bool = True,
        allow_none: bool = False,
    ) -> Optional[str]:
        """Validate a URL."""
        if value is None:
            if allow_none:
                return None
            if not required:
                return None
            raise ValidationError(f"{name} is required")
        
        url_str = str(value).strip()
        
        # Basic URL validation pattern
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        
        if not url_pattern.match(url_str):
            raise ValidationError(f"{name} must be a valid URL")
        
        if len(url_str) > 2048:
            raise ValidationError(f"{name} must be at most 2048 characters")
        
        return url_str

    @staticmethod
    def validate_email(
        value: Any,
        name: str = "email",
        required: bool = True,
        allow_none: bool = False,
    ) -> Optional[str]:
        """Validate an email address."""
        if value is None:
            if allow_none:
                return None
            if not required:
                return None
            raise ValidationError(f"{name} is required")
        
        email_str = str(value).strip().lower()
        
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        if not email_pattern.match(email_str):
            raise ValidationError(f"{name} must be a valid email address")
        
        if len(email_str) > 254:
            raise ValidationError(f"{name} must be at most 254 characters")
        
        return email_str

    @staticmethod
    def validate_datetime(
        value: Any,
        name: str = "datetime",
        required: bool = True,
        allow_none: bool = False,
    ) -> Optional[datetime]:
        """Validate a datetime value (ISO format string or datetime object)."""
        if value is None:
            if allow_none:
                return None
            if not required:
                return None
            raise ValidationError(f"{name} is required")
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                # Try ISO format
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise ValidationError(
                    f"{name} must be a valid ISO format datetime string"
                )
        
        raise ValidationError(f"{name} must be a datetime or ISO format string")

    @staticmethod
    def validate_dict(
        value: Any,
        name: str = "dict",
        required: bool = True,
        allow_none: bool = False,
        schema: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict]:
        """Validate a dictionary with optional schema validation."""
        if value is None:
            if allow_none:
                return None
            if not required:
                return {}
            raise ValidationError(f"{name} is required")
        
        if not isinstance(value, dict):
            raise ValidationError(f"{name} must be a dictionary")
        
        # Schema validation if provided
        if schema:
            validator = InputValidator()
            validated_dict = {}
            
            for key, rules in schema.items():
                if isinstance(rules, dict):
                    required_field = rules.get('required', False)
                    field_type = rules.get('type', str)
                    
                    if key not in value:
                        if required_field:
                            raise ValidationError(f"{name}.{key} is required")
                        continue
                    
                    field_value = value[key]
                    
                    if field_type == str:
                        validated_dict[key] = validator.validate_string(
                            field_value,
                            name=f"{name}.{key}",
                            **{k: v for k, v in rules.items() if k != 'type'}
                        )
                    elif field_type == int:
                        validated_dict[key] = validator.validate_int(
                            field_value,
                            name=f"{name}.{key}",
                            **{k: v for k, v in rules.items() if k != 'type'}
                        )
                    # Add more types as needed
            
            return validated_dict
        
        return value


# Global validator instance
_validator: Optional[InputValidator] = None


def get_validator() -> InputValidator:
    """Get the global InputValidator instance."""
    global _validator
    if _validator is None:
        _validator = InputValidator()
    return _validator


# Convenience validation functions for common use cases

def validate_post_data(post_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate post data from API or user input.
    
    Args:
        post_data: Post data dictionary
        
    Returns:
        Validated post data dictionary
        
    Raises:
        ValidationError: If validation fails
    """
    validator = get_validator()
    
    validated = {}
    
    # Required fields
    validated['content'] = validator.validate_string(
        post_data.get('content'),
        name='content',
        max_length=50000,
        required=False  # Some posts might only have title
    )
    
    validated['title'] = validator.validate_string(
        post_data.get('title'),
        name='title',
        max_length=1000,
        required=False
    )
    
    # At least one of content or title must be present
    if not validated.get('content') and not validated.get('title'):
        raise ValidationError("At least one of 'content' or 'title' must be provided")
    
    # Optional fields with validation
    if 'url' in post_data:
        validated['url'] = validator.validate_url(
            post_data['url'],
            name='url',
            required=False
        )
    
    if 'platform' in post_data:
        validated['platform'] = validator.validate_enum(
            post_data['platform'],
            name='platform',
            allowed_values=['twitter', 'threads', 'telegram', 'github', 'blog'],
            required=False
        )
    
    if 'author' in post_data:
        validated['author'] = validator.validate_string(
            post_data['author'],
            name='author',
            max_length=200,
            required=False
        )
    
    # Copy other fields as-is (they'll be validated by database layer)
    for key, value in post_data.items():
        if key not in validated:
            validated[key] = value
    
    return validated


def validate_search_query(query: str, max_length: int = 1000) -> str:
    """
    Validate a search query string.
    
    Args:
        query: Search query string
        max_length: Maximum query length
        
    Returns:
        Validated query string
        
    Raises:
        ValidationError: If validation fails
    """
    validator = get_validator()
    return validator.validate_string(
        query,
        name='search_query',
        max_length=max_length,
        required=True
    )





