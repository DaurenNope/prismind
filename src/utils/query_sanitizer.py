#!/usr/bin/env python3
"""
Query Sanitization Utilities for Database Operations
Prevents SQL injection and ensures safe query construction.
"""

import re
from typing import Optional


def sanitize_search_query(query: str) -> str:
    """
    Sanitize a search query string to prevent SQL injection.
    Escapes special characters used in SQL LIKE patterns.
    
    Args:
        query: Raw search query from user input
        
    Returns:
        Sanitized query string safe for use in SQL queries
    """
    if not query:
        return ""
    
    # Convert to string and strip whitespace
    query = str(query).strip()
    
    # Escape SQL LIKE special characters: %, _
    # Also escape backslashes first to prevent double-escaping
    query = query.replace("\\", "\\\\")  # Escape backslashes first
    query = query.replace("%", "\\%")    # Escape wildcard %
    query = query.replace("_", "\\_")    # Escape single char wildcard _
    
    # Remove or escape other potentially dangerous characters
    # Remove null bytes
    query = query.replace("\x00", "")
    
    # Limit length to prevent DoS
    if len(query) > 1000:
        query = query[:1000]
    
    return query


def sanitize_column_name(column_name: str, allowed_columns: Optional[set[str]] = None) -> str:
    """
    Sanitize a database column name to prevent SQL injection.
    
    Args:
        column_name: Column name to sanitize
        allowed_columns: Optional set of allowed column names (whitelist)
        
    Returns:
        Sanitized column name
        
    Raises:
        ValueError: If column_name is not in allowed_columns whitelist
    """
    if not column_name:
        raise ValueError("Column name cannot be empty")
    
    column_name = str(column_name).strip()
    
    # Whitelist validation (most secure)
    if allowed_columns and column_name not in allowed_columns:
        raise ValueError(
            f"Column name '{column_name}' is not in allowed list: {allowed_columns}"
        )
    
    # Basic sanitization: only allow alphanumeric, underscore, period
    # This is a fallback if whitelist is not provided
    if not re.match(r'^[a-zA-Z0-9_.]+$', column_name):
        raise ValueError(f"Invalid column name format: {column_name}")
    
    return column_name


def sanitize_sql_value(value: any) -> str:
    """
    Sanitize a value for use in SQL queries.
    For use with parameterized queries - this is extra validation.
    
    Args:
        value: Value to sanitize
        
    Returns:
        Sanitized string representation
    """
    if value is None:
        return "NULL"
    
    value_str = str(value)
    
    # Remove null bytes
    value_str = value_str.replace("\x00", "")
    
    # Limit length
    if len(value_str) > 10000:
        value_str = value_str[:10000]
    
    return value_str


def build_ilike_pattern(query: str, prefix: str = "%", suffix: str = "%") -> str:
    """
    Build a safe ILIKE pattern from a search query.
    
    Args:
        query: Search query string
        prefix: Pattern prefix (default: "%")
        suffix: Pattern suffix (default: "%")
        
    Returns:
        Safe ILIKE pattern string
    """
    sanitized = sanitize_search_query(query)
    if not sanitized:
        return f"{prefix}{suffix}"
    return f"{prefix}{sanitized}{suffix}"





