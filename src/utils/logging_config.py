"""
PrisMind Centralized Logging Configuration
======================================

Provides consistent logging setup across all PrisMind modules.
Includes structured logging, error tracking, and performance monitoring.

Author: PrisMind AI System
"""

import logging
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class PrisMindFormatter(logging.Formatter):
    """Custom formatter for PrisMind with structured output"""
    
    def format(self, record):
        # Add custom fields
        if hasattr(record, 'module'):
            module = record.module
        else:
            module = record.name.split('.')[-1]
            
        # Create base format
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname
        
        # Add context if available
        context = ""
        if hasattr(record, 'context'):
            context = f" [{record.context}]"
        
        # Format message
        message = record.getMessage()
        
        # Color coding for console
        colors = {
            'DEBUG': '\033[36m',      # Cyan
            'INFO': '\033[32m',       # Green
            'WARNING': '\033[33m',    # Yellow
            'ERROR': '\033[31m',      # Red
            'CRITICAL': '\033[35m',    # Magenta
        }
        reset = '\033[0m'
        
        if hasattr(record, 'no_color') and record.no_color:
            color = ""
            reset = ""
        else:
            color = colors.get(level, "")
        
        return f"{color}[{timestamp}] {level:8} {module}{context}: {message}{reset}"


class StructuredLogger:
    """Enhanced logger with structured logging capabilities"""
    
    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self._setup_logger(level)
    
    def _setup_logger(self, level: str):
        """Setup logger with custom formatter and handlers"""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set level
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(PrisMindFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler (optional)
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(
            log_dir / f"prismind_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        # JSON formatter for file logs
        json_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": "%(message)s", '
            '"context": %(context)s}'
        )
        file_handler.setFormatter(json_formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs):
        """Debug level logging with context"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Info level logging with context"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Warning level logging with context"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Error level logging with context"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Critical level logging with context"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Exception level logging with context (same as error but includes exception info)"""
        self._log(logging.ERROR, message, exc_info=True, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with context support"""
        # Add context to log record; ensure 'context' always exists for formatters
        extra = {}
        try:
            if 'context' in kwargs:
                extra['context'] = json.dumps(kwargs['context'])
            else:
                extra['context'] = 'null'
        except Exception:
            extra['context'] = 'null'
        if 'no_color' in kwargs:
            extra['no_color'] = kwargs['no_color']
        
        self.logger.log(level, message, extra=extra)


class PerformanceLogger:
    """Logger for performance monitoring and metrics"""
    
    def __init__(self, name: str = "performance"):
        self.logger = logging.getLogger(f"prismind.{name}")
        self.metrics = {}
    
    def log_execution_time(self, operation: str, duration: float, **context):
        """Log operation execution time"""
        self.logger.info(
            f"Operation '{operation}' completed in {duration:.3f}s",
            context=f"perf|{operation}|{duration:.3f}s|{json.dumps(context)}"
        )
        
        # Track metrics
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append({
            'duration': duration,
            'timestamp': datetime.now().isoformat(),
            'context': context
        })
    
    def log_error_rate(self, operation: str, error_count: int, total_count: int):
        """Log error rate for operations"""
        error_rate = (error_count / total_count) * 100 if total_count > 0 else 0
        self.logger.warning(
            f"Error rate for '{operation}': {error_rate:.1f}% ({error_count}/{total_count})",
            context=f"error_rate|{operation}|{error_rate:.1f}%"
        )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics"""
        summary = {}
        for operation, measurements in self.metrics.items():
            if measurements:
                durations = [m['duration'] for m in measurements]
                summary[operation] = {
                    'count': len(measurements),
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'total_duration': sum(durations)
                }
        return summary


# Global logger instances
_loggers = {}
_perf_logger = None


def get_logger(name: str, level: str = None) -> StructuredLogger:
    """Get or create a structured logger instance"""
    global _loggers
    
    if name not in _loggers:
        # Use environment variable or default level
        log_level = level or os.getenv('PRISMIND_LOG_LEVEL', 'INFO')
        _loggers[name] = StructuredLogger(f"prismind.{name}", log_level)
    
    return _loggers[name]


def get_performance_logger() -> PerformanceLogger:
    """Get the global performance logger"""
    global _perf_logger
    if _perf_logger is None:
        _perf_logger = PerformanceLogger()
    return _perf_logger


def setup_logging():
    """Setup logging for the entire PrisMind application"""
    # Environment-based configuration
    log_level = os.getenv('PRISMIND_LOG_LEVEL', 'INFO')
    log_format = os.getenv('PRISMIND_LOG_FORMAT', 'console')  # console or json
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    if log_format == 'json':
        # JSON format for production
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": "%(message)s"}'
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        # Colored console format for development
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(PrisMindFormatter())
        root_logger.addHandler(handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    # Suppress Supabase client HTTP request logs (very noisy)
    logging.getLogger('postgrest').setLevel(logging.WARNING)
    logging.getLogger('gotrue').setLevel(logging.WARNING)
    logging.getLogger('realtime').setLevel(logging.WARNING)
    # Suppress Supabase client internal logger
    logging.getLogger('supabase').setLevel(logging.WARNING)
    # Suppress Supabase HTTP client logger (logs every request)
    logging.getLogger('_client').setLevel(logging.WARNING)
    
    print(f"📝 Logging configured: level={log_level}, format={log_format}")


def log_function_call(func):
    """Decorator to log function execution time and errors"""
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        perf_logger = get_performance_logger()
        start_time = datetime.now()
        
        try:
            result = func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            perf_logger.log_execution_time(
                func.__name__,
                duration,
                args_count=len(args),
                kwargs_count=len(kwargs)
            )
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            perf_logger.log_execution_time(
                func.__name__,
                duration,
                args_count=len(args),
                kwargs_count=len(kwargs),
                error=str(e)
            )
            raise
    
    return wrapper


# Initialize logging on import (guard against environments where os may be unavailable during import order)
try:
    _env = os.environ  # type: ignore[name-defined]
    _auto_setup = 'PRISMIND_AUTO_SETUP_LOGGING' not in _env
except Exception:
    _auto_setup = False
if _auto_setup:
    setup_logging()
