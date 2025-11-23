import logging
from typing import Dict, Any, Optional
from src.agents.base_agent import BaseAgent, AgentStatus
from langchain_core.messages import BaseMessage, AIMessage
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class SpecializedAgent(BaseAgent):
    """
    Base class for specialized agents in the new graph architecture.
    Wraps the existing BaseAgent functionality but adds LangGraph compatibility.
    Includes retry logic and error handling for robust operation.
    """
    def __init__(self, agent_id: str, agent_name: str, role: str):
        super().__init__(agent_id=agent_id, agent_name=agent_name, agent_version="1.0.0")
        self.role = role

    async def initialize(self) -> bool:
        """
        Initialize the agent resources.
        """
        self._mark_initialized()
        return True

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task (Legacy/Base compatibility).
        Wraps process() if possible, or returns error.
        Includes Retry Logic via Tenacity.
        """
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
        
        # Define retry strategy: 3 attempts, exponential backoff
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(Exception),
            reraise=True
        )
        async def _execute_with_retry():
            # Adapt task to state if possible
            state = {"messages": [], "artifacts": task, "current_agent": "user", "task_status": "running"}
            return await self.process(state)

        try:
            return await _execute_with_retry()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Agent {self.agent_name} failed after retries: {e}")
            return {"error": str(e), "status": "failed"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the current state and return updates with retry logic.
        This method includes automatic retry on failure with exponential backoff.
        """
        try:
            return await self._process_impl(state)
        except Exception as e:
            logger.error(f"{self.agent_name} failed: {e}", exc_info=True)
            raise

    async def _process_impl(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implementation - must be overridden by subclasses.
        This is the actual processing logic that will be retried on failure.
        """
        raise NotImplementedError
