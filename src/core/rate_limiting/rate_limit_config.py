"""
Rate limiting configuration module
"""

import json
import os
from typing import Dict, Any, Optional


class RateLimitConfig:
    """Configuration for rate limiting"""
    
    def __init__(self, 
                 requests_per_minute: int = 30,
                 requests_per_hour: int = 1000,
                 burst_limit: int = 5,
                 base_delay: float = 2.0,
                 max_delay: float = 60.0,
                 backoff_multiplier: float = 1.5,
                 jitter_range: tuple = (0.5, 1.5)):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter_range = jitter_range
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'requests_per_minute': self.requests_per_minute,
            'requests_per_hour': self.requests_per_hour,
            'burst_limit': self.burst_limit,
            'base_delay': self.base_delay,
            'max_delay': self.max_delay,
            'backoff_multiplier': self.backoff_multiplier,
            'jitter_range': self.jitter_range
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'RateLimitConfig':
        """Create config from dictionary"""
        return cls(**config_dict)
    
    @classmethod
    def from_file(cls, config_file: str) -> 'RateLimitConfig':
        """Load config from JSON file"""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config_dict = json.load(f)
                return cls.from_dict(config_dict)
            else:
                return cls()  # Return default config
        except Exception as e:
            print(f"⚠️ Error loading config from {config_file}: {e}")
            return cls()  # Return default config
    
    def save_to_file(self, config_file: str):
        """Save config to JSON file"""
        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            print(f"⚠️ Error saving config to {config_file}: {e}")
    
    def __str__(self) -> str:
        return f"RateLimitConfig(rpm={self.requests_per_minute}, rph={self.requests_per_hour}, burst={self.burst_limit})"
    
    def __repr__(self) -> str:
        return self.__str__()





