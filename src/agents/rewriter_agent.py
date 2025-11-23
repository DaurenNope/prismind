#!/usr/bin/env python3
"""
Rewriter Agent

Refactored ContentRewriter as a BaseAgent implementation.
Provides persona-based content rewriting with quality validation.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

from src.domain.intelligence.agents.base_agent import AgentError, AgentStatus, BaseAgent
from src.domain.publishing.circuit_breaker import get_circuit_breaker
from src.domain.publishing.engagement_learner import EngagementLearner
from src.domain.publishing.fact_validator import FactValidator
from src.domain.publishing.rag_system import ExampleVectorDatabase
from src.domain.publishing.thread_splitter import ThreadSplitter
from src.domain.publishing.voice_validator import VoiceValidator

logger = logging.getLogger(__name__)


class RewriterAgent(BaseAgent):
    """
    Rewriter Agent for persona-based content rewriting.
    
    Inherits from BaseAgent and provides:
    - Persona-based rewriting
    - Multi-persona generation
    - Quality validation
    - Batch processing
    """

    def __init__(
        self,
        agent_id: str = "rewriter_agent",
        agent_name: str = "Rewriter Agent",
        agent_version: str = "1.0.0",
        dependencies: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the Rewriter Agent.

        Args:
            agent_id: Unique identifier for the agent
            agent_name: Human-readable name for the agent
            agent_version: Version string for the agent
            dependencies: List of other agent IDs this agent depends on
            config: Optional configuration dictionary
        """
        super().__init__(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_version=agent_version,
            dependencies=dependencies or [],
        )
        
        self.config = config or {}
        self.personas: Dict[str, Dict[str, Any]] = {}
        self.voice_patterns: Dict[str, Dict[str, Any]] = {}
        self.opinions: Dict[str, Dict[str, Any]] = {}
        self.voice_examples: Dict[str, List[Dict[str, Any]]] = {}
        self.rewrite_rules: Dict[str, Any] = {}
        
        # Initialize components (will be loaded in initialize)
        self.fact_validator: Optional[FactValidator] = None
        self.thread_splitter: Optional[ThreadSplitter] = None
        self.voice_validator: Optional[VoiceValidator] = None
        self.engagement_learner: Optional[EngagementLearner] = None
        self.vector_db: Optional[ExampleVectorDatabase] = None
        self.circuit_breaker = get_circuit_breaker()
        
        # LLM configuration
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        self.gemini_api_keys: List[str] = []
        self.current_key_index = 0
        
        # Batch processing configuration
        self.batch_size = self.config.get("batch_size", 5)
        self.max_parallel_personas = self.config.get("max_parallel_personas", 3)
        
        # Quality thresholds
        self.min_quality_score = self.config.get("min_quality_score", 70)
        self.min_voice_consistency = self.config.get("min_voice_consistency", 80)
        
        # Metrics
        self.rewrite_metrics = {
            "total_rewrites": 0,
            "successful_rewrites": 0,
            "failed_rewrites": 0,
            "quality_scores": [],
            "voice_scores": [],
            "fact_scores": [],
            "rewrite_times": [],
        }

    async def initialize(self) -> bool:
        """
        Initialize the Rewriter Agent.

        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            self._set_status(AgentStatus.RUNNING)
            logger.info(f"Initializing {self.agent_name}...")
            
            # Load personas
            self.personas = self._load_personas()
            logger.info(f"Loaded {len(self.personas)} personas")
            
            # Load voice patterns and opinions
            self.voice_patterns = self._load_voice_patterns()
            self.opinions = self._load_opinions()
            self.voice_examples = self._load_voice_examples()
            self.rewrite_rules = self._load_rewrite_rules()
            
            # Initialize validators
            self.fact_validator = FactValidator()
            self.thread_splitter = ThreadSplitter(max_length=280)
            
            try:
                self.voice_validator = VoiceValidator()
                logger.info("✅ Voice validator initialized")
            except Exception as e:
                logger.warning(f"⚠️ Voice validator not available: {e}")
                self.voice_validator = None
            
            try:
                self.engagement_learner = EngagementLearner()
                logger.info("✅ Engagement learner initialized")
            except Exception as e:
                logger.warning(f"⚠️ Engagement learner not available: {e}")
                self.engagement_learner = None
            
            # Initialize vector database
            try:
                vector_path = os.getenv("VECTOR_DB_PATH", "data/vector_db")
                self.vector_db = ExampleVectorDatabase(storage_path=vector_path)
                stats = self.vector_db.get_stats()
                logger.info(
                    "✅ Persona RAG DB ready (%s examples, faiss=%s)",
                    stats.get("total_examples", 0),
                    stats.get("faiss_available"),
                )
            except Exception as e:
                logger.warning(f"⚠️ Persona RAG DB not available: {e}")
                self.vector_db = None
            
            # Load API keys
            self.gemini_api_keys = self._load_gemini_keys()
            if not self.gemini_api_keys:
                logger.warning("No Gemini API keys found")
            
            # Load analytics if available
            try:
                from src.domain.publishing.rewrite_analytics import get_analytics
                self.analytics = get_analytics()
            except Exception as e:
                logger.warning(f"Analytics not available: {e}")
                self.analytics = None
            
            self._mark_initialized()
            logger.info(f"✅ {self.agent_name} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.agent_name}: {e}", exc_info=True)
            self._set_status(AgentStatus.ERROR)
            raise AgentError(
                f"Initialization failed: {e}",
                agent_id=self.agent_id,
            ) from e

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a rewriting task.

        Task format:
        {
            "action": "rewrite" | "rewrite_multi_persona" | "batch_rewrite" | "validate_quality",
            "analyzed_content": {...},  # Required for rewrite actions
            "persona": "persona_id",  # Required for single rewrite
            "personas": ["persona1", "persona2"],  # Required for multi-persona
            "platform": "twitter" | "threads" | "auto",
            "batch": [...],  # Required for batch_rewrite
            "content": "...",  # Required for validate_quality
            ...
        }

        Args:
            task: Task dictionary containing action and parameters

        Returns:
            Dictionary containing execution results
        """
        start_time = time.time()
        action = task.get("action", "rewrite")
        
        try:
            self._set_status(AgentStatus.RUNNING)
            
            if action == "rewrite":
                result = await self._rewrite_single(task)
            elif action == "rewrite_multi_persona":
                result = await self._rewrite_multi_persona(task)
            elif action == "batch_rewrite":
                result = await self._batch_rewrite(task)
            elif action == "validate_quality":
                result = await self._validate_quality(task)
            else:
                raise AgentError(
                    f"Unknown action: {action}",
                    agent_id=self.agent_id,
                    details={"available_actions": ["rewrite", "rewrite_multi_persona", "batch_rewrite", "validate_quality"]},
                )
            
            execution_time = time.time() - start_time
            self._update_execution_metrics(execution_time, success=True)
            self.record_metric("rewrite_latency", execution_time)
            
            self._set_status(AgentStatus.IDLE)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_execution_metrics(execution_time, success=False)
            self.metrics["last_error"] = str(e)
            self._set_status(AgentStatus.ERROR)
            
            logger.error(f"Task execution failed: {e}", exc_info=True)
            raise AgentError(
                f"Task execution failed: {e}",
                agent_id=self.agent_id,
                details={"action": action, "error": str(e)},
            ) from e

    async def _rewrite_single(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rewrite content for a single persona.

        Args:
            task: Task dictionary with analyzed_content and persona

        Returns:
            Rewritten content dictionary
        """
        analyzed_content = task.get("analyzed_content")
        if not analyzed_content:
            raise AgentError(
                "analyzed_content is required",
                agent_id=self.agent_id,
            )
        
        persona = task.get("persona")
        if not persona:
            raise AgentError(
                "persona is required",
                agent_id=self.agent_id,
            )
        
        platform = task.get("platform", "auto")
        
        # Use the existing rewrite_analyzed_post method from ContentRewriter
        # We'll need to port this method
        result = await self.rewrite_analyzed_post(
            analyzed_content=analyzed_content,
            persona=persona,
            platform=platform,
        )
        
        # Update metrics
        self.rewrite_metrics["total_rewrites"] += 1
        if "error" not in result:
            self.rewrite_metrics["successful_rewrites"] += 1
            if "quality_score" in result:
                self.rewrite_metrics["quality_scores"].append(result["quality_score"])
            if "voice_consistency_score" in result:
                self.rewrite_metrics["voice_scores"].append(result["voice_consistency_score"])
            if "fact_preservation_score" in result:
                self.rewrite_metrics["fact_scores"].append(result["fact_preservation_score"])
        else:
            self.rewrite_metrics["failed_rewrites"] += 1
        
        # Publish event
        self.publish_event(
            "rewriter.rewrite_complete",
            {
                "persona": persona,
                "platform": platform,
                "success": "error" not in result,
                "quality_score": result.get("quality_score"),
            },
        )
        
        return result

    async def _rewrite_multi_persona(
        self, task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate rewrites for multiple personas in parallel.

        Args:
            task: Task dictionary with analyzed_content and personas list

        Returns:
            Dictionary with rewrites for each persona
        """
        analyzed_content = task.get("analyzed_content")
        if not analyzed_content:
            raise AgentError("analyzed_content is required", agent_id=self.agent_id)
        
        personas = task.get("personas", [])
        if not personas:
            # Default to all available personas
            personas = list(self.personas.keys())
        
        platform = task.get("platform", "auto")
        
        # Limit parallel execution
        max_parallel = min(len(personas), self.max_parallel_personas)
        
        # Create tasks for parallel execution
        tasks = []
        for persona in personas:
            if persona not in self.personas:
                logger.warning(f"Unknown persona: {persona}, skipping")
                continue
            
            tasks.append(
                self.rewrite_analyzed_post(
                    analyzed_content=analyzed_content,
                    persona=persona,
                    platform=platform,
                )
            )
        
        # Execute in parallel with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def bounded_rewrite(task_coro):
            async with semaphore:
                return await task_coro
        
        results = await asyncio.gather(
            *[bounded_rewrite(task) for task in tasks],
            return_exceptions=True,
        )
        
        # Process results
        persona_results = {}
        quality_scores = {}
        
        for i, persona in enumerate(personas):
            if i >= len(results):
                continue
            
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Error rewriting for {persona}: {result}")
                persona_results[persona] = {"error": str(result)}
                continue
            
            persona_results[persona] = result
            if "quality_score" in result:
                quality_scores[persona] = result["quality_score"]
        
        # Select best persona based on quality score
        best_persona = None
        best_score = 0
        for persona, score in quality_scores.items():
            if score > best_score:
                best_score = score
                best_persona = persona
        
        # Update metrics
        self.rewrite_metrics["total_rewrites"] += len(personas)
        successful = sum(1 for r in persona_results.values() if "error" not in r)
        self.rewrite_metrics["successful_rewrites"] += successful
        self.rewrite_metrics["failed_rewrites"] += len(personas) - successful
        
        # Publish event
        self.publish_event(
            "rewriter.multi_persona_complete",
            {
                "personas": personas,
                "best_persona": best_persona,
                "best_score": best_score,
                "successful": successful,
                "total": len(personas),
            },
        )
        
        return {
            "persona_results": persona_results,
            "best_persona": best_persona,
            "best_score": best_score,
            "quality_scores": quality_scores,
        }

    async def _batch_rewrite(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process multiple posts in batch.

        Args:
            task: Task dictionary with batch list

        Returns:
            Dictionary with results for each item in batch
        """
        batch = task.get("batch", [])
        if not batch:
            raise AgentError(
                "batch is required",
                agent_id=self.agent_id,
            )
        
        platform = task.get("platform", "auto")
        persona = task.get("persona")  # Optional: if specified, use for all
        
        # Process in batches
        batch_size = task.get("batch_size", self.batch_size)
        results = []
        errors = []
        
        for i in range(0, len(batch), batch_size):
            batch_items = batch[i : i + batch_size]
            
            # Create tasks for this batch
            batch_tasks = []
            for item in batch_items:
                analyzed_content = item.get("analyzed_content", item)
                item_persona = item.get("persona", persona)
                
                if not item_persona:
                    errors.append(
                        {
                            "item": item.get("post_id", "unknown"),
                            "error": "No persona specified",
                        }
                    )
                    continue
                
                batch_tasks.append(
                    self.rewrite_analyzed_post(
                        analyzed_content=analyzed_content,
                        persona=item_persona,
                        platform=platform,
                    )
                )
            
            # Execute batch
            batch_results = await asyncio.gather(
                *batch_tasks, return_exceptions=True
            )
            
            # Process results
            for j, result in enumerate(batch_results):
                item = batch_items[j]
                if isinstance(result, Exception):
                    errors.append(
                        {
                            "item": item.get("post_id", "unknown"),
                            "error": str(result),
                        }
                    )
                else:
                    results.append(result)
            
            # Publish progress event
            self.publish_event(
                "rewriter.batch_progress",
                {
                    "processed": len(results),
                    "total": len(batch),
                    "errors": len(errors),
                },
            )
        
        # Update metrics
        self.rewrite_metrics["total_rewrites"] += len(batch)
        self.rewrite_metrics["successful_rewrites"] += len(results)
        self.rewrite_metrics["failed_rewrites"] += len(errors)
        
        # Publish completion event
        self.publish_event(
            "rewriter.batch_complete",
            {
                "total": len(batch),
                "successful": len(results),
                "failed": len(errors),
            },
        )
        
        return {
            "results": results,
            "errors": errors,
            "total": len(batch),
            "successful": len(results),
            "failed": len(errors),
        }

    async def _validate_quality(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate quality of rewritten content.

        Args:
            task: Task dictionary with content and persona

        Returns:
            Quality validation results
        """
        content = task.get("content")
        if not content:
            raise AgentError(
                "content is required",
                agent_id=self.agent_id,
            )
        
        persona = task.get("persona")
        if not persona:
            raise AgentError(
                "persona is required",
                agent_id=self.agent_id,
            )
        
        original_content = task.get("original_content", "")
        
        # Perform quality checks
        quality_result = await self._validate_rewrite_quality(
            rewritten=content,
            original=original_content,
            persona=persona,
        )
        
        return quality_result

    async def rewrite_analyzed_post(
        self,
        analyzed_content: Dict[str, Any],
        persona: str,
        platform: str = "auto",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Rewrite an analyzed post for a specific persona.
        
        This method maintains backward compatibility with ContentRewriter.
        It delegates to the original implementation.
        
        Args:
            analyzed_content: Full analysis from IntelligentContentAnalyzer
            persona: Persona to use
            platform: Target platform
            **kwargs: Additional options
            
        Returns:
            Rewritten content dictionary
        """
        # Use ModularRewriter via compat layer (replaces deprecated ContentRewriter)
        from src.domain.publishing.modular_rewriter.compat import CompatRewriter
        
        # Create compat rewriter instance (uses ModularRewriter under the hood)
        rewriter = CompatRewriter()
        
        # Call the compatibility method (same signature as ContentRewriter.rewrite_analyzed_post)
        result = await rewriter.rewrite_analyzed_post(
            analyzed_content=analyzed_content,
            persona=persona,
            platform=platform,
            **kwargs,
        )
        
        # Update key index for rotation
        self.current_key_index = rewriter.current_key_index
        
        return result

    async def _validate_rewrite_quality(
        self,
        rewritten: str,
        original: str,
        persona: str,
    ) -> Dict[str, Any]:
        """
        Validate rewrite quality including fact accuracy, voice match, and appropriateness.

        Args:
            rewritten: Rewritten content
            original: Original content
            persona: Target persona

        Returns:
            Quality validation results
        """
        validation_result = {
            "rewrite_quality": {"score": 0, "valid": False, "issues": []},
            "fact_accuracy": {"score": 0, "valid": False, "issues": []},
            "voice_match": {"score": 0, "valid": False, "issues": []},
            "content_appropriateness": {"score": 0, "valid": False, "issues": []},
            "overall_valid": False,
        }
        
        # 1. Rewrite quality validation
        if self.voice_validator:
            quality_score = self._score_output_quality(rewritten, persona)
            validation_result["rewrite_quality"] = quality_score
        
        # 2. Fact accuracy checking
        if self.fact_validator and original:
            fact_validation = self.fact_validator.validate_preservation(
                original_text=original,
                rewritten_text=rewritten,
            )
            validation_result["fact_accuracy"] = {
                "score": fact_validation.get("preservation_score", 0),
                "valid": fact_validation.get("valid", False),
                "issues": fact_validation.get("warnings", []),
                "details": fact_validation,
            }
        
        # 3. Voice match verification
        if self.voice_validator:
            voice_validation = self.voice_validator.validate_voice(
                text=rewritten,
                persona=persona,
                return_details=True,
            )
            validation_result["voice_match"] = {
                "score": voice_validation.get("consistency_score", 0),
                "valid": voice_validation.get("is_consistent", False),
                "issues": voice_validation.get("issues", []),
                "details": voice_validation,
            }
        
        # 4. Content appropriateness checking
        appropriateness = self._check_content_appropriateness(rewritten, persona)
        validation_result["content_appropriateness"] = appropriateness
        
        # Calculate overall validity
        scores = [
            validation_result["rewrite_quality"].get("score", 0),
            validation_result["fact_accuracy"].get("score", 0),
            validation_result["voice_match"].get("score", 0),
            validation_result["content_appropriateness"].get("score", 0),
        ]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        validation_result["overall_score"] = avg_score
        validation_result["overall_valid"] = (
            avg_score >= self.min_quality_score
            and validation_result["rewrite_quality"].get("valid", False)
            and validation_result["fact_accuracy"].get("valid", False)
            and validation_result["voice_match"].get("valid", False)
        )
        
        return validation_result

    def _check_content_appropriateness(
        self, content: str, persona: str
    ) -> Dict[str, Any]:
        """
        Check if content is appropriate for the persona.

        Args:
            content: Content to check
            persona: Target persona

        Returns:
            Appropriateness validation results
        """
        issues = []
        score = 100
        
        persona_info = self.personas.get(persona, {})
        persona_language = persona_info.get("language", "english")
        
        # Check language match
        if persona_language == "russian":
            # Check for Russian characters
            has_russian = any(
                char in content
                for char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
            )
            if not has_russian:
                score -= 30
                issues.append("Content not in Russian (persona requires Russian)")
        else:
            # Check for excessive Russian in English persona
            russian_chars = sum(
                1
                for char in content
                if char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
            )
            if russian_chars > len(content) * 0.1:
                score -= 20
                issues.append("Excessive Russian content in English persona")
        
        # Check for persona-specific appropriateness
        if persona == "aspandead":
            # Should have personal, emotional elements
            personal_indicators = ["i", "me", "my", "felt", "seems", "wondering"]
            personal_count = sum(
                1 for indicator in personal_indicators if indicator in content.lower()
            )
            if personal_count < 2:
                score -= 15
                issues.append("Not personal enough for Aspandead")
        
        return {
            "score": max(0, score),
            "valid": score >= 70,
            "issues": issues,
        }

    def _score_output_quality(
        self, rewritten: str, persona: str
    ) -> Dict[str, Any]:
        """
        Score rewritten content quality.

        Args:
            rewritten: Rewritten content
            persona: Target persona

        Returns:
            Quality score dictionary
        """
        issues = []
        score = 100
        
        if not rewritten or not rewritten.strip():
            return {"score": 0, "quality": "failed", "issues": ["Empty content"], "valid": False}
        
        content_length = len(rewritten.strip())
        
        # Length penalties
        if content_length < 20:
            score -= 30
            issues.append("Too short (< 20 chars)")
        elif content_length < 50:
            score -= 15
            issues.append("Very short (< 50 chars)")
        elif content_length > 1000:
            score -= 10
            issues.append("Too long (> 1000 chars)")
        
        # Check for forbidden elements (from rewrite rules)
        import re
        
        # Emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "\U0001F900-\U0001F9FF"
            "\U0001FA70-\U0001FAFF"
            "]+",
            flags=re.UNICODE,
        )
        emoji_matches = emoji_pattern.findall(rewritten)
        if emoji_matches:
            score -= 20
            issues.append(f"Contains {len(emoji_matches)} emoji(s)")
        
        # Hashtags
        hashtag_pattern = re.compile(r"#\w+")
        hashtag_matches = hashtag_pattern.findall(rewritten)
        if hashtag_matches:
            score -= 15
            issues.append(f"Contains {len(hashtag_matches)} hashtag(s)")
        
        # Corporate language
        corporate_phrases = [
            "join us",
            "follow for more",
            "don't miss out",
            "click the link",
            "subscribe now",
        ]
        found_corporate = [
            phrase for phrase in corporate_phrases if phrase in rewritten.lower()
        ]
        if found_corporate:
            score -= 10
            issues.append(f"Corporate language detected: {found_corporate[:2]}")
        
        return {
            "score": max(0, score),
            "quality": "excellent" if score >= 90 else "good" if score >= 70 else "needs_improvement",
            "issues": issues,
            "valid": score >= self.min_quality_score,
        }

    # Helper methods for loading configuration
    def _load_personas(self) -> Dict[str, Dict[str, Any]]:
        """Load personas from configuration."""
        from pathlib import Path
        
        config_dir = Path("config/personas")
        personas = {}
        
        if config_dir.exists():
            for persona_file in config_dir.glob("*.json"):
                if persona_file.name.endswith("_examples.json"):
                    continue
                
                try:
                    import json
                    with open(persona_file, "r", encoding="utf-8") as f:
                        persona_data = json.load(f)
                        persona_key = persona_file.stem
                        personas[persona_key] = persona_data
                except Exception as e:
                    logger.warning(f"Failed to load persona {persona_file}: {e}")
        
        return personas

    def _load_voice_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load voice patterns from configuration."""
        from pathlib import Path
        import json
        
        config_file = Path("config/voice_patterns.json")
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load voice patterns: {e}")
        return {}

    def _load_opinions(self) -> Dict[str, Dict[str, Any]]:
        """Load opinions from configuration."""
        from pathlib import Path
        import json
        
        config_file = Path("config/opinions.json")
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load opinions: {e}")
        return {}

    def _load_voice_examples(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load voice examples from configuration."""
        from pathlib import Path
        import json
        
        examples = {}
        config_dir = Path("config/personas")
        
        if config_dir.exists():
            for example_file in config_dir.glob("*_examples.json"):
                persona_key = example_file.stem.replace("_examples", "")
                try:
                    with open(example_file, "r", encoding="utf-8") as f:
                        examples[persona_key] = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load examples for {persona_key}: {e}")
        
        return examples

    def _load_rewrite_rules(self) -> Dict[str, Any]:
        """Load rewrite rules from configuration."""
        from pathlib import Path
        import json
        
        config_file = Path("config/rewrite_rules.json")
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load rewrite rules: {e}")
        return {}

    def _load_gemini_keys(self) -> List[str]:
        """Load Gemini API keys from environment."""
        keys = []
        
        primary_key = os.getenv("GEMINI_API_KEY")
        if primary_key:
            keys.append(primary_key)
        
        i = 1
        while True:
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if not key:
                break
            keys.append(key)
            i += 1
        
        return keys

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the Rewriter Agent.

        Returns:
            Health check results including metrics
        """
        base_health = await super().health_check()
        
        # Add rewrite-specific metrics
        rewrite_metrics = {
            "total_rewrites": self.rewrite_metrics["total_rewrites"],
            "successful_rewrites": self.rewrite_metrics["successful_rewrites"],
            "failed_rewrites": self.rewrite_metrics["failed_rewrites"],
            "success_rate": (
                self.rewrite_metrics["successful_rewrites"]
                / max(self.rewrite_metrics["total_rewrites"], 1)
                * 100
            ),
            "avg_quality_score": (
                sum(self.rewrite_metrics["quality_scores"])
                / max(len(self.rewrite_metrics["quality_scores"]), 1)
                if self.rewrite_metrics["quality_scores"]
                else 0
            ),
            "avg_voice_score": (
                sum(self.rewrite_metrics["voice_scores"])
                / max(len(self.rewrite_metrics["voice_scores"]), 1)
                if self.rewrite_metrics["voice_scores"]
                else 0
            ),
            "avg_fact_score": (
                sum(self.rewrite_metrics["fact_scores"])
                / max(len(self.rewrite_metrics["fact_scores"]), 1)
                if self.rewrite_metrics["fact_scores"]
                else 0
            ),
        }
        
        base_health["rewrite_metrics"] = rewrite_metrics
        base_health["personas_loaded"] = len(self.personas)
        base_health["components"] = {
            "fact_validator": self.fact_validator is not None,
            "voice_validator": self.voice_validator is not None,
            "engagement_learner": self.engagement_learner is not None,
            "vector_db": self.vector_db is not None,
            "circuit_breaker": self.circuit_breaker is not None,
        }
        
        return base_health


# Singleton instance
_rewriter_agent: Optional[RewriterAgent] = None


def get_rewriter_agent(
    config: Optional[Dict[str, Any]] = None,
) -> RewriterAgent:
    """
    Get singleton instance of RewriterAgent.

    Args:
        config: Optional configuration dictionary

    Returns:
        RewriterAgent singleton instance
    """
    global _rewriter_agent
    if _rewriter_agent is None:
        _rewriter_agent = RewriterAgent(config=config)
    return _rewriter_agent

