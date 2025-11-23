import json
import logging
from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from src.agents.specialized.base_specialized import SpecializedAgent
from src.core.memory.vector_memory import VectorMemory

logger = logging.getLogger(__name__)

class HistorianAgent(SpecializedAgent):
    """
    The Historian: Provides context from long-term memory (Vector DB).
    Returns structured JSON output with historical context information.
    """
    def __init__(self):
        super().__init__(agent_id="historian", agent_name="The Historian", role="Context Retrieval")
        self.memory = VectorMemory()

    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check for Historian Agent"""
        base_health = await super().health_check()
        
        # Add agent-specific health
        agent_health = {
            **base_health,
            "memory_available": self.memory is not None,
            "last_retrieval": self.metrics.get("last_retrieval_time"),
            "retrieval_count": self.metrics.get("retrieval_count", 0),
        }
        
        return agent_health

    async def _process_impl(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("📚 Historian checking archives...")
        
        target_post = state.get("artifacts", {}).get("current_post", {})
        query = target_post.get("content", "") or target_post.get("title", "")
        
        if not query:
             return {
                "messages": [AIMessage(content="Historian: No query context.")],
                "current_agent": "historian",
                "artifacts": {
                    "historical_context": {
                        "context": "",
                        "relevant_memories": [],
                        "match_count": 0,
                        "error": "No query provided"
                    }
                }
            }

        try:
            # Search memory
            import time
            start_time = time.time()
            context = await self.memory.get_context(query)
            memories = await self.memory.search_memory(query, limit=5)
            retrieval_time = time.time() - start_time
            
            # Update metrics
            self.metrics["last_retrieval_time"] = time.time()
            self.metrics["retrieval_count"] = self.metrics.get("retrieval_count", 0) + 1
            self.record_metric("retrieval_duration", retrieval_time)
            
            # Structure the response
            historical_data = {
                "context": context,
                "relevant_memories": [
                    {
                        "content": m.get("content", ""),
                        "type": m.get("type", "unknown"),
                        "source_id": m.get("source_id"),
                        "metadata": m.get("metadata", {})
                    }
                    for m in memories
                ],
                "match_count": len(memories),
                "query": query
            }
            
            if not context:
                msg = "No relevant history found."
            else:
                msg = f"Found {len(memories)} relevant memory(ies): {context[:100]}..."

            return {
                "messages": [AIMessage(content=f"Historian Report: {msg}")],
                "artifacts": {"historical_context": historical_data},
                "current_agent": "historian",
                "task_status": "history_complete"
            }
        except Exception as e:
            logger.error(f"Historian search failed: {e}", exc_info=True)
            return {
                "messages": [AIMessage(content=f"Historian: Error retrieving context - {str(e)}")],
                "artifacts": {
                    "historical_context": {
                        "context": "",
                        "relevant_memories": [],
                        "match_count": 0,
                        "error": str(e)
                    }
                },
                "current_agent": "historian"
            }
