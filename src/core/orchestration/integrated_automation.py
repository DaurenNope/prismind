#!/usr/bin/env python3
"""
Integrated Automation Orchestrator

Combines new AgentGraph with existing FullAutomationLoop
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.application.orchestration.agent_graph import AgentGraph
from src.pipeline.full_automation_loop import FullAutomationLoop
from src.domain.publishing.worker import get_publisher_worker
from src.domain.intelligence.agents.collection_orchestrator_agent import get_collection_orchestrator_agent
from src.domain.intelligence.agents.registry import get_registry
from src.domain.collection.extractors.social_extractor_base import SocialPost
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class IntegratedAutomationOrchestrator:
    """
    Unified orchestrator that combines:
    - New AgentGraph (LangGraph-based multi-agent system)
    - Existing FullAutomationLoop (collection → analysis → publishing)
    - PublisherWorker (automatic content posting)
    """

    def __init__(self):
        # New system
        self.agent_graph = AgentGraph()

        # Existing systems
        self.automation_loop = FullAutomationLoop()
        self.publisher_worker = get_publisher_worker()
        self.collection_agent = get_collection_orchestrator_agent()
        self.registry = get_registry()

        self._running = False

    async def initialize(self):
        """Initialize all systems"""
        logger.info("🚀 Initializing Integrated Automation Orchestrator...")

        # 1. Register agents with existing framework (includes messaging setup)
        from src.application.orchestration.agent_registration import register_specialized_agents

        # Check if agents are already registered to avoid duplicates
        specialized_agent_ids = ["analyst", "skeptic", "historian"]
        already_registered = all(
            self.registry.get_agent(agent_id) is not None
            for agent_id in specialized_agent_ids
        )

        if not already_registered:
            # Register agents with framework (includes messaging setup)
            agents = await register_specialized_agents()
            # Agents are already registered and initialized by register_specialized_agents()
            logger.info(f"✅ Registered {len(agents)} specialized agents with framework")
        else:
            logger.info("✅ Specialized agents already registered, skipping duplicate registration")

        # 2. Start publisher worker (CRITICAL)
        if not self.publisher_worker._started:
            self.publisher_worker.start()
            logger.info("✅ Publisher worker started")

        logger.info("✅ Integrated Automation Orchestrator initialized")

    async def run_cycle(self, use_agent_graph: bool = True):
        """
        Run one complete automation cycle

        Args:
            use_agent_graph: If True, use new AgentGraph for analysis
                            If False, use existing analysis system
        """
        logger.info("=" * 70)
        logger.info("🔄 Starting Integrated Automation Cycle")
        logger.info("=" * 70)

        try:
            # Step 1: Collection (existing system)
            logger.info("📥 Step 1: Collection")
            collection_results = await self.automation_loop.run_collection()
            logger.info(f"✅ Collected: {collection_results}")

            # Step 2: Analysis (new or existing system)
            if use_agent_graph:
                logger.info("🧠 Step 2: Analysis (AgentGraph)")
                analysis_results = await self._run_agent_graph_analysis()
            else:
                logger.info("🧠 Step 2: Analysis (Existing)")
                analysis_results = await self.automation_loop.run_analysis()

            logger.info(f"✅ Analyzed: {analysis_results}")

            # Step 3: Transformation & Scheduling (existing system)
            logger.info("✍️ Step 3: Transformation & Scheduling")
            scheduling_results = await self.automation_loop.run_transformation_and_scheduling(
                auto_schedule=True  # CRITICAL: Auto-schedule posts
            )
            logger.info(f"✅ Scheduled: {scheduling_results}")

            # Step 4: Publishing (automatic via worker)
            logger.info("📤 Step 4: Publishing (automatic via worker)")
            # Worker automatically picks up scheduled posts
            # Just verify it's running
            if not self.publisher_worker._started:
                logger.warning("⚠️ Publisher worker not running!")
                self.publisher_worker.start()

            return {
                "collection": collection_results,
                "analysis": analysis_results,
                "scheduling": scheduling_results,
                "publishing": "automatic",
            }

        except Exception as e:
            logger.error(f"❌ Cycle failed: {e}", exc_info=True)
            raise

    async def _run_agent_graph_analysis(self):
        """Run analysis using new AgentGraph system"""
        # Get unanalyzed posts
        unanalyzed = self.automation_loop.db.get_unanalyzed_posts(limit=10)

        analyzed = 0
        failed = 0

        for post in unanalyzed:
            try:
                # Parse created_at from string to datetime if needed
                created_at = post.get("created_at")
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    except Exception:
                        # Fallback to current time if parsing fails
                        created_at = datetime.now()
                elif not isinstance(created_at, datetime):
                    created_at = datetime.now()

                # Parse JSON strings for hashtags, engagement, media_urls
                hashtags = post.get("hashtags", [])
                if isinstance(hashtags, str):
                    try:
                        hashtags = json.loads(hashtags)
                    except Exception:
                        hashtags = []

                engagement = post.get("engagement", {})
                if isinstance(engagement, str):
                    try:
                        engagement = json.loads(engagement)
                    except Exception:
                        engagement = {}

                media_urls = post.get("media_urls", [])
                if isinstance(media_urls, str):
                    try:
                        media_urls = json.loads(media_urls)
                    except Exception:
                        media_urls = []

                # Convert post to SocialPost format
                social_post = SocialPost(
                    post_id=post.get("post_id") or post.get("id"),
                    platform=post.get("platform") or post.get("source", "unknown"),
                    content=post.get("content", ""),
                    author=post.get("author", ""),
                    author_handle=post.get("author_handle") or post.get("username", ""),
                    url=post.get("url", ""),
                    created_at=created_at,
                    hashtags=hashtags,
                    engagement=engagement,
                    media_urls=media_urls,
                    post_type=post.get("post_type", "post"),
                )

                # Run through agent graph
                initial_state = {
                    "messages": [],
                    "current_agent": "user",
                    "next_agent": "director",
                    "task_status": "started",
                    "artifacts": {"current_post": post},
                    "errors": [],
                }

                # Collect final state by accumulating all node outputs
                final_state = initial_state.copy()
                async for output in self.agent_graph.app.astream(initial_state):
                    # LangGraph astream yields dict where keys are node names
                    # Merge all state updates
                    for node_name, state_update in output.items():
                        if isinstance(state_update, dict):
                            # Merge state updates
                            if "messages" in state_update:
                                final_state.setdefault("messages", []).extend(state_update["messages"])
                            if "artifacts" in state_update:
                                final_state.setdefault("artifacts", {}).update(state_update["artifacts"])
                            if "errors" in state_update:
                                final_state.setdefault("errors", []).extend(state_update["errors"])
                            # Update other fields
                            for key, value in state_update.items():
                                if key not in ["messages", "artifacts", "errors"]:
                                    final_state[key] = value

                # Extract analysis from final state
                artifacts = final_state.get("artifacts", {})
                analysis_result = artifacts.get("analysis_result", {})
                verification_result = artifacts.get("verification_result", {})
                historical_context = artifacts.get("historical_context", "")

                # Map agent graph results to existing analysis format
                if analysis_result or verification_result or historical_context:
                    # Convert agent graph results to standard analysis format
                    mapped_analysis = {
                        "ai_summary": analysis_result.get("summary") or analysis_result.get("ai_summary", ""),
                        "value_score": analysis_result.get("value_score", 0),
                        "quality_score": analysis_result.get("quality_score", 0),
                        "key_concepts": analysis_result.get("key_concepts", []),
                        "tags": analysis_result.get("tags", []),
                        "topic": analysis_result.get("topic", ""),
                        "category": analysis_result.get("category", ""),
                        "sentiment": analysis_result.get("sentiment", "Neutral"),
                        "analyzed_at": datetime.now(timezone.utc).isoformat(),
                        "analysis_model": "agent-graph",
                    }
                    
                    # Add verification insights if available
                    if verification_result:
                        mapped_analysis["insights"] = verification_result.get("insights", [])
                        mapped_analysis["verification_status"] = verification_result.get("status", "unknown")
                    
                    # Add historical context if available
                    if historical_context:
                        mapped_analysis["historical_context"] = historical_context
                    
                    # Store using existing database update mechanism
                    try:
                        from src.infrastructure.database.manager import get_supabase_manager
                        db_manager = get_supabase_manager()
                        if db_manager:
                            # Update post with analysis results
                            update_data = {
                                "ai_summary": mapped_analysis.get("ai_summary"),
                                "value_score": mapped_analysis.get("value_score"),
                                "quality_score": mapped_analysis.get("quality_score"),
                                "key_concepts": json.dumps(mapped_analysis.get("key_concepts", [])),
                                "tags": json.dumps(mapped_analysis.get("tags", [])),
                                "topic": mapped_analysis.get("topic"),
                                "category": mapped_analysis.get("category"),
                                "sentiment": mapped_analysis.get("sentiment"),
                                "analyzed_at": mapped_analysis.get("analyzed_at"),
                                "analysis_model": mapped_analysis.get("analysis_model"),
                            }
                            db_manager.client.table("posts").update(update_data).eq(
                                "post_id", post.get("post_id") or post.get("id")
                            ).execute()
                            analyzed += 1
                        else:
                            logger.warning("Database manager not available, analysis not stored")
                            analyzed += 1  # Still count as analyzed
                    except Exception as e:
                        logger.error(f"Failed to store analysis for post {post.get('post_id')}: {e}")
                        failed += 1
                else:
                    logger.warning(f"No analysis results extracted for post {post.get('post_id')}")
                    failed += 1

            except Exception as e:
                logger.error(f"Failed to analyze post {post.get('post_id')}: {e}")
                failed += 1

        return {"analyzed": analyzed, "failed": failed}

    async def run_forever(self, interval_minutes: int = 60, use_agent_graph: bool = True):
        """Run continuously"""
        await self.initialize()
        self._running = True

        while self._running:
            try:
                await self.run_cycle(use_agent_graph=use_agent_graph)
            except Exception as e:
                logger.error(f"Cycle error: {e}")

            logger.info(f"⏳ Waiting {interval_minutes} minutes until next cycle...")
            await asyncio.sleep(interval_minutes * 60)

    def stop(self):
        """Stop the orchestrator"""
        self._running = False
        self.publisher_worker.stop()

