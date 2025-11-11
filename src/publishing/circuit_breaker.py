"""
Circuit Breaker for API Rate Limits
Prevents burning through all API keys when they're exhausted
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # All APIs exhausted, stop trying
    HALF_OPEN = "half_open"  # Testing if APIs recovered


class APICircuitBreaker:
    """
    Circuit breaker that tracks API failures and prevents
    unnecessary calls when all APIs are exhausted.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,  # Open after 5 consecutive failures
        recovery_timeout: int = 3600,  # Try again after 1 hour
        success_threshold: int = 2  # Need 2 successes to close
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        
        # Per-provider tracking (Gemini, Mistral, Ollama)
        self.provider_states: Dict[str, Dict] = {
            "gemini": {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "last_failure": None,
                "exhausted_keys": []  # Track which keys are exhausted
            },
            "mistral": {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "last_failure": None,
                "exhausted_keys": []
            },
            "ollama": {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "last_failure": None
            }
        }
    
    def can_call(self, provider: str = "gemini") -> bool:
        """
        Check if we can make an API call for this provider.
        
        Returns:
            True if circuit is closed and we can try
            False if circuit is open (all exhausted)
        """
        provider_state = self.provider_states.get(provider, {})
        
        # Check global state first
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._should_attempt_recovery():
                logger.info(f"🔄 Circuit breaker: Attempting recovery (half-open)")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        
        # Check provider-specific state
        if provider_state.get("state") == CircuitState.OPEN:
            if self._should_attempt_recovery(provider):
                provider_state["state"] = CircuitState.HALF_OPEN
                provider_state["failure_count"] = 0
                return True
            return False
        
        return True
    
    def record_success(self, provider: str = "gemini"):
        """Record a successful API call"""
        self.success_count += 1
        self.failure_count = 0
        self.last_success_time = datetime.now()
        
        provider_state = self.provider_states.get(provider, {})
        provider_state["failure_count"] = 0
        
        # If in half-open, need multiple successes to close
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.success_threshold:
                logger.info(f"✅ Circuit breaker: CLOSED (recovered after {self.success_count} successes)")
                self.state = CircuitState.CLOSED
                self.success_count = 0
        
        if provider_state.get("state") == CircuitState.HALF_OPEN:
            if provider_state["failure_count"] == 0:
                logger.info(f"✅ Provider {provider}: Circuit CLOSED (recovered)")
                provider_state["state"] = CircuitState.CLOSED
    
    def record_failure(
        self,
        provider: str = "gemini",
        error_type: str = "rate_limit",
        api_key_index: Optional[int] = None
    ):
        """
        Record a failed API call.
        
        Args:
            provider: API provider (gemini, mistral, ollama)
            error_type: Type of error (rate_limit, timeout, etc.)
            api_key_index: Which API key failed (for tracking exhausted keys)
        """
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = datetime.now()
        
        provider_state = self.provider_states.get(provider, {})
        provider_state["failure_count"] = provider_state.get("failure_count", 0) + 1
        provider_state["last_failure"] = datetime.now()
        
        # Track exhausted keys
        if error_type == "rate_limit" and api_key_index is not None:
            exhausted = provider_state.get("exhausted_keys", [])
            if api_key_index not in exhausted:
                exhausted.append(api_key_index)
                provider_state["exhausted_keys"] = exhausted
                logger.warning(f"⚠️ {provider} key #{api_key_index + 1} exhausted (rate limit)")
        
        # Open circuit if threshold reached
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.error(
                    f"🚫 Circuit breaker: OPENED "
                    f"({self.failure_count} consecutive failures, "
                    f"will retry after {self.recovery_timeout}s)"
                )
                self.state = CircuitState.OPEN
        
        # Open provider-specific circuit
        if provider_state["failure_count"] >= self.failure_threshold:
            if provider_state.get("state") != CircuitState.OPEN:
                logger.error(
                    f"🚫 Provider {provider}: Circuit OPENED "
                    f"({provider_state['failure_count']} failures)"
                )
                provider_state["state"] = CircuitState.OPEN
    
    def all_providers_exhausted(self) -> bool:
        """Check if all API providers are exhausted"""
        return all(
            state.get("state") == CircuitState.OPEN
            for state in self.provider_states.values()
        )
    
    def get_exhausted_keys(self, provider: str = "gemini") -> List[int]:
        """Get list of exhausted API keys for a provider"""
        return self.provider_states.get(provider, {}).get("exhausted_keys", [])
    
    def _should_attempt_recovery(self, provider: Optional[str] = None) -> bool:
        """Check if enough time has passed to attempt recovery"""
        if provider:
            provider_state = self.provider_states.get(provider, {})
            last_failure = provider_state.get("last_failure")
        else:
            last_failure = self.last_failure_time
        
        if not last_failure:
            return True
        
        elapsed = (datetime.now() - last_failure).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def get_status(self) -> Dict:
        """Get current circuit breaker status"""
        return {
            "global_state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success": self.last_success_time.isoformat() if self.last_success_time else None,
            "providers": {
                provider: {
                    "state": state.get("state", CircuitState.CLOSED).value,
                    "failure_count": state.get("failure_count", 0),
                    "exhausted_keys": state.get("exhausted_keys", []),
                    "last_failure": state.get("last_failure").isoformat() if state.get("last_failure") else None
                }
                for provider, state in self.provider_states.items()
            }
        }


# Global circuit breaker instance
_global_circuit_breaker: Optional[APICircuitBreaker] = None


def get_circuit_breaker() -> APICircuitBreaker:
    """Get global circuit breaker instance"""
    global _global_circuit_breaker
    if _global_circuit_breaker is None:
        _global_circuit_breaker = APICircuitBreaker()
    return _global_circuit_breaker


def reset_circuit_breaker():
    """Reset circuit breaker (for testing)"""
    global _global_circuit_breaker
    _global_circuit_breaker = APICircuitBreaker()

