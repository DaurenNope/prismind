"""
Scout Agent - Real content collection
"""
import logging
from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from src.agents.specialized.base_specialized import SpecializedAgent
from src.agents.collection_orchestrator_agent import get_collection_orchestrator_agent

logger = logging.getLogger(__name__)


class ScoutAgent(SpecializedAgent):
    """
    The Scout: Finds and collects new content from platforms
    """
    def __init__(self):
        super().__init__(agent_id="scout", agent_name="The Scout", role="Content Discovery")
        self.collection_agent = get_collection_orchestrator_agent()

    async def initialize(self) -> bool:
        """Initialize collection agent"""
        await super().initialize()
        # Ensure collection agent is initialized
        if not self.collection_agent._initialized:
            await self.collection_agent.initialize()
        return True

    async def _process_impl(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect new content from platforms
        """
        logger.info("🔭 Scout collecting content from platforms...")

        try:
            # Use existing collection agent
            result = await self.collection_agent.collect_all()

            # Extract posts from result
            posts = []
            if isinstance(result, dict):
                # Result format: {"total": X, "platforms": {...}}
                for platform, platform_result in result.items():
                    if platform not in ["total", "errors", "error_details", "started_at", "completed_at", "total_duration_seconds", "success_count", "failure_count"]:
                        if isinstance(platform_result, dict):
                            count = platform_result.get("count", 0)
                            if count > 0:
                                # Get actual posts from database
                                from src.services.new_database_manager import get_database_manager
                                db = get_database_manager()
                                platform_posts = db.get_posts_by_platform(platform, limit=count)
                                posts.extend(platform_posts)

            if not posts:
                return {
                    "messages": [AIMessage(content="Scout: No new content found.")],
                    "artifacts": {"current_post": None, "posts_collected": 0},
                    "current_agent": "scout",
                    "task_status": "scouting"
                }

            # Return first post for processing (or can process all)
            first_post = posts[0] if posts else None

            return {
                "messages": [AIMessage(content=f"Scout: Found {len(posts)} new post(s).")],
                "artifacts": {
                    "current_post": first_post,
                    "all_posts": posts,
                    "posts_collected": len(posts),
                    "collection_result": result
                },
                "current_agent": "scout",
                "task_status": "scouting"
            }

        except Exception as e:
            logger.error(f"Scout collection failed: {e}", exc_info=True)
            return {
                "messages": [AIMessage(content=f"Scout: Collection failed - {str(e)}")],
                "artifacts": {"current_post": None, "posts_collected": 0},
                "errors": [str(e)],
                "current_agent": "scout",
                "task_status": "error"
            }
