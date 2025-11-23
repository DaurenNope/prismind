#!/usr/bin/env python3
"""
Analysis Agent for BEYONDLINES

Refactored from IntelligentContentAnalyzer to inherit from BaseAgent.
Provides AI-powered content analysis with multi-provider fallback, caching,
quality scoring, and batch processing.

Author: BEYONDLINES AI System
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.domain.intelligence.agents.base_agent import AgentError, AgentStatus, BaseAgent
from src.domain.collection.extractors.social_extractor_base import SocialPost
from src.domain.analysis.analyzers.scoring import (
    guess_language,
    guess_topic,
    guess_type,
    is_rewrite_candidate,
    score_quality,
    score_value,
)
from src.domain.publishing.persona_matcher import get_persona_matcher
from src.shared.utils.diary_storage import DiaryStorage

logger = logging.getLogger(__name__)


class ProviderHealth:
    """Tracks health status of AI providers"""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.is_healthy = True
        self.failure_count = 0
        self.success_count = 0
        self.last_success: Optional[float] = None
        self.last_failure: Optional[float] = None
        self.consecutive_failures = 0
        self.total_requests = 0
        self.total_latency = 0.0

    def record_success(self, latency: float) -> None:
        """Record a successful request"""
        self.is_healthy = True
        self.success_count += 1
        self.last_success = time.time()
        self.consecutive_failures = 0
        self.total_requests += 1
        self.total_latency += latency

    def record_failure(self) -> None:
        """Record a failed request"""
        self.failure_count += 1
        self.last_failure = time.time()
        self.consecutive_failures += 1
        self.total_requests += 1

        # Mark unhealthy after 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.is_healthy = False

    def get_avg_latency(self) -> float:
        """Get average latency in seconds"""
        if self.success_count == 0:
            return 0.0
        return self.total_latency / self.success_count

    def get_success_rate(self) -> float:
        """Get success rate (0-1)"""
        if self.total_requests == 0:
            return 1.0
        return self.success_count / self.total_requests

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for metrics"""
        return {
            "provider": self.provider_name,
            "healthy": self.is_healthy,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.get_success_rate(),
            "avg_latency": self.get_avg_latency(),
            "consecutive_failures": self.consecutive_failures,
            "last_success": self.last_success,
            "last_failure": self.last_failure,
        }


class EnhancedAnalysisCache:
    """Enhanced cache for analysis results with metrics"""

    def __init__(self, ttl_hours: int = 1):
        self.cache: Dict[str, tuple[datetime, Dict[str, Any]]] = {}
        self.ttl = timedelta(hours=ttl_hours)
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result if still valid"""
        if cache_key in self.cache:
            cached_time, result = self.cache[cache_key]
            if datetime.now() - cached_time < self.ttl:
                self.hits += 1
                return result
            else:
                # Expired, remove it
                del self.cache[cache_key]
                self.evictions += 1

        self.misses += 1
        return None

    def set(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Store analysis result with current timestamp"""
        self.cache[cache_key] = (datetime.now(), result)

    def invalidate(self, cache_key: str) -> None:
        """Invalidate a specific cache entry"""
        if cache_key in self.cache:
            del self.cache[cache_key]
            self.evictions += 1

    def clear(self) -> None:
        """Clear all cached results"""
        self.cache.clear()
        self.evictions += len(self.cache)

    def get_hit_rate(self) -> float:
        """Get cache hit rate (0-1)"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": self.get_hit_rate(),
            "size": len(self.cache),
        }


class AnalysisAgent(BaseAgent):
    """
    Analysis Agent for BEYONDLINES

    Provides AI-powered content analysis with:
    - Multi-provider fallback (Mistral, Gemini, Ollama)
    - Analysis caching
    - Quality scoring
    - Batch processing
    - Provider health monitoring
    """

    def __init__(
        self,
        agent_id: str = "analysis_agent",
        agent_name: str = "Analysis Agent",
        agent_version: str = "2.0.0",
        dependencies: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the Analysis Agent"""
        super().__init__(agent_id, agent_name, agent_version, dependencies)

        # Load configuration
        self.config = config or self._load_config()

        # Initialize components
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self._diary: Optional[DiaryStorage] = None
        try:
            self._diary = DiaryStorage()
        except Exception as e:
            logger.warning(f"Diary storage not available: {e}")

        # Initialize AI services
        self.ai_services: List[Dict[str, Any]] = []
        self.provider_health: Dict[str, ProviderHealth] = {}
        self._init_ai_services()

        # Initialize cache
        cache_ttl = self.config.get("cache", {}).get("ttl_hours", 1)
        self.cache = EnhancedAnalysisCache(ttl_hours=cache_ttl)

        # Rate limiting
        self._min_interval_s = 60.0 / self.config.get("rate_limit", {}).get("rpm", 30)
        self._last_call_ts = 0.0

        # Batch processing
        self.batch_size = self.config.get("batch_processing", {}).get("batch_size", 5)
        self.max_workers = self.config.get("batch_processing", {}).get("max_workers", 3)

        # Metrics
        self.analysis_count = 0
        self.batch_count = 0
        self.provider_rotation_count = 0

        logger.info(
            f"✅ {self.agent_name} initialized with {len(self.ai_services)} AI services"
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment"""
        config_path = os.path.join(
            os.path.dirname(__file__), "config", "analysis_agent.yaml"
        )
        config: Dict[str, Any] = {
            "cache": {"ttl_hours": 1},
            "rate_limit": {"rpm": 30, "tpm": 200000, "rpd": 250},
            "batch_processing": {"batch_size": 5, "max_workers": 3},
            "providers": {
                "primary": os.getenv("ANALYZER_PRIMARY", "gemini"),
                "fallback_enabled": True,
                "health_check_interval": 300,
            },
        }

        # Try to load from YAML if available
        try:
            import yaml

            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    file_config = yaml.safe_load(f)
                    config.update(file_config)
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}")

        return config

    def _init_ai_services(self) -> None:
        """Initialize available AI services in order of preference"""
        # Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            gem_model_name = os.getenv("ANALYZER_GEMINI_MODEL", "gemini-2.5-flash-lite")
            vision_model_name = os.getenv(
                "ANALYZER_GEMINI_VISION_MODEL", "gemini-1.5-pro-vision-latest"
            )
            self.ai_services.append(
                {
                    "name": "gemini",
                    "model": genai.GenerativeModel(gem_model_name),
                    "vision_model": genai.GenerativeModel(vision_model_name),
                }
            )
            self.provider_health["gemini"] = ProviderHealth("gemini")
            logger.info("✅ Google Gemini initialized")

        # Mistral
        mistral_key = os.getenv("MISTRAL_API_KEY")
        if mistral_key:
            self.ai_services.append(
                {
                    "name": "mistral",
                    "key": mistral_key,
                    "base_url": "https://api.mistral.ai/v1",
                    "model": "mistral-small-latest",
                }
            )
            self.provider_health["mistral"] = ProviderHealth("mistral")
            logger.info("✅ Mistral AI initialized")

        # Ollama
        ollama_url = os.getenv("OLLAMA_URL")
        if ollama_url:
            self.ai_services.append(
                {
                    "name": "ollama",
                    "url": ollama_url.rstrip("/"),
                    "model": os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
                    "options": {"num_predict": 150, "temperature": 0.3},
                }
            )
            self.provider_health["ollama"] = ProviderHealth("ollama")
            logger.info("✅ Ollama initialized")

        # Reorder based on primary preference
        primary = self.config.get("providers", {}).get("primary", "gemini")
        if primary and primary in [s["name"] for s in self.ai_services]:
            # Move primary to front
            services_by_name = {s["name"]: s for s in self.ai_services}
            new_order = [services_by_name[primary]]
            for s in self.ai_services:
                if s["name"] != primary:
                    new_order.append(s)
            self.ai_services = new_order

        if not self.ai_services:
            logger.warning("⚠️ No AI services available, using basic analysis")

    async def initialize(self) -> bool:
        """Initialize the agent"""
        try:
            self._set_status(AgentStatus.IDLE)
            self._mark_initialized()

            # Publish initialization event
            self.publish_event("agent.initialized", {"agent_id": self.agent_id})

            logger.info(f"✅ {self.agent_name} initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize {self.agent_name}: {e}", exc_info=True)
            self._set_status(AgentStatus.ERROR)
            raise AgentError(f"Initialization failed: {e}", agent_id=self.agent_id)

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an analysis task

        Task format:
        {
            "action": "analyze" | "analyze_batch",
            "post": SocialPost | Dict,  # Single post
            "posts": List[SocialPost | Dict],  # Multiple posts for batch
            "include_comments": bool,
            "include_media": bool,
        }
        """
        start_time = time.time()
        self._set_status(AgentStatus.RUNNING)

        try:
            action = task.get("action", "analyze")

            if action == "analyze":
                result = await self._analyze_single(task)
            elif action == "analyze_batch":
                result = await self._analyze_batch(task)
            else:
                raise AgentError(
                    f"Unknown action: {action}", agent_id=self.agent_id
                )

            execution_time = time.time() - start_time
            self._update_execution_metrics(execution_time, True)
            self._set_status(AgentStatus.IDLE)

            # Publish completion event
            self.publish_event(
                "analysis.complete",
                {
                    "agent_id": self.agent_id,
                    "action": action,
                    "execution_time": execution_time,
                },
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self._update_execution_metrics(execution_time, False)
            self._set_status(AgentStatus.ERROR)
            self.metrics["last_error"] = str(e)

            logger.error(f"❌ Analysis task failed: {e}", exc_info=True)
            raise AgentError(f"Analysis failed: {e}", agent_id=self.agent_id)

    async def _analyze_single(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single post"""
        post_data = task.get("post")
        if not post_data:
            raise AgentError("No post provided in task", agent_id=self.agent_id)

        # Convert dict to SocialPost if needed
        if isinstance(post_data, dict):
            post = SocialPost(**post_data)
        else:
            post = post_data

        include_comments = task.get("include_comments", True)
        include_media = task.get("include_media", True)

        # Use existing analyze_bookmark method
        result = await asyncio.to_thread(
            self.analyze_bookmark, post, include_comments, include_media
        )

        self.analysis_count += 1
        self.record_metric("analysis_count", self.analysis_count)

        return {"analysis": result, "post_id": post.post_id}

    async def _analyze_batch(
        self, task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze multiple posts in parallel"""
        posts_data = task.get("posts", [])
        if not posts_data:
            raise AgentError("No posts provided in batch task", agent_id=self.agent_id)

        include_comments = task.get("include_comments", True)
        include_media = task.get("include_media", True)

        # Convert dicts to SocialPost objects
        posts: List[SocialPost] = []
        for post_data in posts_data:
            if isinstance(post_data, dict):
                posts.append(SocialPost(**post_data))
            else:
                posts.append(post_data)

        # Process in batches
        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_post = {
                executor.submit(
                    self.analyze_bookmark, post, include_comments, include_media
                ): post
                for post in posts
            }

            # Process completed tasks
            for future in as_completed(future_to_post):
                post = future_to_post[future]
                try:
                    result = future.result()
                    results.append({"post_id": post.post_id, "analysis": result})
                except Exception as e:
                    logger.error(f"❌ Analysis failed for post {post.post_id}: {e}")
                    errors.append({"post_id": post.post_id, "error": str(e)})

        self.batch_count += 1
        self.analysis_count += len(results)
        self.record_metric("batch_count", self.batch_count)
        self.record_metric("analysis_count", self.analysis_count)

        return {
            "results": results,
            "errors": errors,
            "total": len(posts),
            "successful": len(results),
            "failed": len(errors),
        }

    def analyze_bookmark(
        self,
        post: SocialPost,
        include_comments: bool = True,
        include_media: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze a bookmark with AI services

        This is the main analysis method, maintaining backward compatibility
        with IntelligentContentAnalyzer.
        """
        logger.info(f"🔍 Analyzing {post.platform} post: {post.post_id}")

        # Check for cancellation
        try:
            from src.services.cancel_manager import is_cancelled

            if is_cancelled("analysis"):
                raise Exception("Cancelled")
        except Exception:
            pass

        # Deterministic mode for testing
        if os.getenv("DETERMINISTIC_ANALYSIS", "0") == "1":
            return self._deterministic_analysis(
                post, include_comments=include_comments, include_media=include_media
            )

        # Generate cache key
        language = getattr(post, "language", None) or "unknown"
        content_str = f"{post.content or ''}{post.url or ''}{language}"
        cache_key = hashlib.md5(content_str.encode("utf-8")).hexdigest()

        # Check cache
        cached_result = self.cache.get(cache_key)
        if cached_result:
            logger.debug(f"📦 Cache hit for post {post.post_id}")
            cached_result = cached_result.copy()
            cached_result["post_id"] = post.post_id
            cached_result["platform"] = post.platform
            cached_result["analyzed_at"] = datetime.now().isoformat()
            self.record_metric("cache_hits", self.cache.hits)
            return cached_result

        # Initialize analysis result
        analysis = {
            "post_id": post.post_id,
            "platform": post.platform,
            "analyzed_at": datetime.now().isoformat(),
            "analysis_version": "2.0",
            "ai_analysis_succeeded": False,
            "ai_service_used": None,
        }

        # Core content analysis with provider fallback
        try:
            core_analysis = self._analyze_core_content_with_fallback(post)
            if isinstance(core_analysis, dict):
                if (
                    core_analysis.get("analysis_version") != "fallback"
                    and core_analysis.get("ai_summary")
                ):
                    analysis["ai_analysis_succeeded"] = True
                    analysis["ai_service_used"] = core_analysis.get(
                        "analysis_model", "unknown"
                    )
                else:
                    analysis["ai_analysis_succeeded"] = False
                    analysis["ai_service_used"] = None

                if not isinstance(core_analysis, dict):
                    core_analysis = self._basic_analysis(
                        post,
                        self.sentiment_analyzer.polarity_scores(post.content or ""),
                    )
                    analysis["ai_analysis_succeeded"] = False
                    analysis["ai_service_used"] = None

                analysis.update(core_analysis)
        except Exception as e:
            logger.error(f"⚠️ Core content analysis failed: {e}")
            core_analysis = self._basic_analysis(
                post, self.sentiment_analyzer.polarity_scores(post.content or "")
            )
            analysis["ai_analysis_succeeded"] = False
            analysis["ai_service_used"] = None
            if isinstance(core_analysis, dict):
                analysis.update(core_analysis)

        # Comment analysis (Reddit only)
        if include_comments and post.platform == "reddit":
            try:
                comment_analysis = self._analyze_comments(post)
                analysis["comment_insights"] = comment_analysis
            except Exception as e:
                logger.error(f"⚠️ Comment analysis failed: {e}")
                analysis["comment_insights"] = []

        # Media analysis
        enable_vision = os.getenv("ENABLE_VISION_ANALYSIS", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        media_only = bool(post.media_urls) and not (
            post.content and str(post.content).strip()
        )
        if include_media and post.media_urls and (enable_vision or media_only):
            valid_media_urls = [
                url
                for url in post.media_urls
                if isinstance(url, str)
                and (url.startswith("http://") or url.startswith("https://"))
            ]
            if valid_media_urls:
                try:
                    media_analysis = self._analyze_media_content(valid_media_urls)
                    analysis["media_insights"] = media_analysis
                except Exception as e:
                    logger.error(f"⚠️ Media analysis failed: {e}")
                    analysis["media_insights"] = {
                        "total_media": len(valid_media_urls),
                        "analyzed_media": 0,
                        "insights": [],
                    }

        # Time sensitivity detection
        try:
            ts = self._detect_time_sensitivity(post, analysis)
            if isinstance(ts, dict):
                analysis.update(ts)
        except Exception as e:
            logger.error(f"⚠️ Time sensitivity detection failed: {e}")

        # Quality scoring
        try:
            value_score = self._calculate_intelligent_value_score(analysis, post)
            analysis["intelligent_value_score"] = value_score
        except Exception as e:
            logger.error(f"⚠️ Value scoring failed: {e}")
            analysis["intelligent_value_score"] = 0.0

        try:
            content_quality_score = self._calculate_content_quality_score(
                analysis, post
            )
            analysis["content_quality_score"] = content_quality_score
        except Exception as e:
            logger.error(f"⚠️ Quality scoring failed: {e}")
            analysis["content_quality_score"] = 0.0

        # Rewrite readiness assessment
        try:
            is_rewrite = self._determine_rewrite_candidate(
                analysis, post, analysis.get("content_quality_score", 0.0)
            )
            analysis["is_rewrite_candidate"] = is_rewrite
        except Exception as e:
            logger.error(f"⚠️ Rewrite candidate assessment failed: {e}")
            analysis["is_rewrite_candidate"] = False

        # Confidence scores
        try:
            confidence = self._calculate_confidence_score(analysis, post)
            analysis["confidence_score"] = confidence
        except Exception as e:
            logger.error(f"⚠️ Confidence scoring failed: {e}")
            analysis["confidence_score"] = 0.5

        # Actionable insights
        try:
            actionable_insights = self._generate_actionable_insights(analysis, post)
            analysis["actionable_insights"] = actionable_insights
        except Exception as e:
            logger.error(f"⚠️ Actionable insights generation failed: {e}")
            analysis["actionable_insights"] = []

        # Learning recommendations
        try:
            learning_recs = self._generate_learning_recommendations(analysis, post)
            analysis["learning_recommendations"] = learning_recs
        except Exception as e:
            logger.error(f"⚠️ Learning recommendations generation failed: {e}")
            analysis["learning_recommendations"] = []

        # Persona matching
        try:
            from src.services.persona_matcher import get_persona_matcher

            matcher = get_persona_matcher()
            persona_recommendations = matcher.get_recommended_personas(analysis)

            analysis["recommended_personas"] = persona_recommendations.get(
                "recommended_personas", []
            )
            analysis["persona_match_scores"] = persona_recommendations.get(
                "persona_match_scores", {}
            )
            analysis["persona_candidacy"] = persona_recommendations.get(
                "persona_candidacy", {}
            )
        except Exception as e:
            logger.error(f"⚠️ Persona matching failed: {e}")
            analysis["recommended_personas"] = []
            analysis["persona_match_scores"] = {}
            analysis["persona_candidacy"] = {}

        logger.info(
            f"✅ Analysis complete - Value Score: {analysis.get('intelligent_value_score', 0.0)}/10"
        )

        # Cache successful analyses
        if analysis and isinstance(analysis, dict):
            if analysis.get("ai_analysis_succeeded") or analysis.get("ai_summary"):
                self.cache.set(cache_key, analysis)
                logger.debug(f"📦 Cached analysis for post {post.post_id}")

        return analysis

    def _analyze_core_content_with_fallback(
        self, post: SocialPost
    ) -> Dict[str, Any]:
        """
        Analyze core content with automatic provider fallback

        Tries providers in order, falling back to next on failure.
        Tracks provider health and rotates if needed.
        """
        sentiment_scores = self.sentiment_analyzer.polarity_scores(
            post.content or ""
        )
        prompt = self._create_analysis_prompt(post)

        # Get healthy providers in priority order
        healthy_providers = [
            s for s in self.ai_services if self._is_provider_healthy(s["name"])
        ]

        # If no healthy providers, try all (they might have recovered)
        if not healthy_providers:
            healthy_providers = self.ai_services
            logger.warning("⚠️ No healthy providers, trying all providers")

        # Try each provider
        for service in healthy_providers:
            provider_name = service["name"]
            start_time = time.time()

            try:
                result = None

                if provider_name == "ollama":
                    result = self._analyze_with_ollama(prompt, sentiment_scores, service)
                elif provider_name == "mistral":
                    result = self._analyze_with_mistral(prompt, sentiment_scores, service)
                elif provider_name == "gemini":
                    req_tokens = self._estimate_tokens(prompt)
                    self._rate_limit_guard(req_tokens)
                    result = self._analyze_with_gemini(prompt, sentiment_scores, service)
                else:
                    continue

                # Success - record and return
                latency = time.time() - start_time
                if provider_name in self.provider_health:
                    self.provider_health[provider_name].record_success(latency)
                self.provider_rotation_count += 1

                if result:
                    result = self._coerce_analysis(post, result)
                    return result

            except Exception as e:
                logger.error(f"⚠️ {provider_name} analysis failed: {e}")
                if provider_name in self.provider_health:
                    self.provider_health[provider_name].record_failure()
                continue

        # All providers failed - use basic analysis
        logger.warning("⚠️ All AI providers failed, using basic analysis")
        return self._coerce_analysis(
            post, self._basic_analysis(post, sentiment_scores)
        )

    def _is_provider_healthy(self, provider_name: str) -> bool:
        """Check if a provider is healthy"""
        if provider_name not in self.provider_health:
            return True  # Unknown providers are assumed healthy
        return self.provider_health[provider_name].is_healthy

    def _rate_limit_guard(self, requested_tokens: int) -> None:
        """Rate limiting guard"""
        now = int(time.time())
        limits = {
            "rpm": self.config.get("rate_limit", {}).get("rpm", 30),
            "tpm": self.config.get("rate_limit", {}).get("tpm", 200000),
            "rpd": self.config.get("rate_limit", {}).get("rpd", 250),
        }
        window_min = now // 60
        window_day = now // 86400
        state = getattr(self, "_rl_state", None) or {
            "min": window_min,
            "min_calls": 0,
            "min_tokens": 0,
            "day": window_day,
            "day_calls": 0,
        }

        # Reset windows
        if state["min"] != window_min:
            state.update({"min": window_min, "min_calls": 0, "min_tokens": 0})
        if state["day"] != window_day:
            state.update({"day": window_day, "day_calls": 0})

        # Wait if limits exceeded
        sleep_interval = 0.5
        while (
            state["min_calls"] + 1 > limits["rpm"]
            or state["min_tokens"] + requested_tokens > limits["tpm"]
            or state["day_calls"] + 1 > limits["rpd"]
        ):
            time.sleep(sleep_interval)
            now = int(time.time())
            window_min = now // 60
            window_day = now // 86400
            if state["min"] != window_min:
                state.update({"min": window_min, "min_calls": 0, "min_tokens": 0})
            if state["day"] != window_day:
                state.update({"day": window_day, "day_calls": 0})

        # Account usage
        state["min_calls"] += 1
        state["min_tokens"] += requested_tokens
        state["day_calls"] += 1
        self._rl_state = state

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count"""
        try:
            return max(1, int(len(text) / 4))
        except Exception:
            return len(text)

    # Import analysis methods from intelligent_content_analyzer
    # These will be implemented by importing or copying the methods
    def _create_analysis_prompt(self, post: SocialPost) -> str:
        """Create analysis prompt - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._create_analysis_prompt(post)

    def _analyze_with_gemini(
        self, prompt: str, sentiment_scores: Dict, service: Dict
    ) -> Dict[str, Any]:
        """Analyze with Gemini - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._analyze_with_gemini(prompt, sentiment_scores, service)

    def _analyze_with_mistral(
        self, prompt: str, sentiment_scores: Dict, service: Dict
    ) -> Dict[str, Any]:
        """Analyze with Mistral - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._analyze_with_mistral(prompt, sentiment_scores, service)

    def _analyze_with_ollama(
        self, prompt: str, sentiment_scores: Dict, service: Dict
    ) -> Dict[str, Any]:
        """Analyze with Ollama - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._analyze_with_ollama(prompt, sentiment_scores, service)

    def _coerce_analysis(
        self, post: SocialPost, analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coerce analysis to proper format - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._coerce_analysis(post, analysis)

    def _basic_analysis(
        self, post: SocialPost, sentiment_scores: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Basic fallback analysis - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._basic_analysis(post, sentiment_scores)

    def _detect_time_sensitivity(
        self, post: SocialPost, analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect time sensitivity - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._detect_time_sensitivity(post, analysis)

    def _calculate_intelligent_value_score(
        self, analysis: Dict[str, Any], post: SocialPost
    ) -> float:
        """Calculate intelligent value score - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._calculate_intelligent_value_score(analysis, post)

    def _calculate_content_quality_score(
        self, analysis: Dict[str, Any], post: SocialPost
    ) -> float:
        """Calculate content quality score - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._calculate_content_quality_score(analysis, post)

    def _determine_rewrite_candidate(
        self, analysis: Dict[str, Any], post: SocialPost, quality_score: float
    ) -> bool:
        """Determine rewrite candidate - use scoring module"""
        return is_rewrite_candidate(analysis, post, quality_score)

    def _calculate_confidence_score(
        self, analysis: Dict[str, Any], post: SocialPost
    ) -> float:
        """Calculate confidence score (0-1)"""
        confidence = 0.5  # Base confidence

        # Increase if AI succeeded
        if analysis.get("ai_analysis_succeeded"):
            confidence += 0.2

        # Increase based on analysis quality
        ai_summary_len = len(analysis.get("ai_summary", "") or "")
        if ai_summary_len >= 150:
            confidence += 0.1
        if ai_summary_len >= 200:
            confidence += 0.05

        # Increase if has tags and concepts
        if analysis.get("tags") and analysis.get("key_concepts"):
            confidence += 0.1

        # Increase if has category
        if analysis.get("category"):
            confidence += 0.05

        return round(min(confidence, 0.95), 2)

    def _generate_actionable_insights(
        self, analysis: Dict[str, Any], post: SocialPost
    ) -> List[str]:
        """Generate actionable insights - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._generate_actionable_insights(analysis, post)

    def _generate_learning_recommendations(
        self, analysis: Dict[str, Any], post: SocialPost
    ) -> List[str]:
        """Generate learning recommendations - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._generate_learning_recommendations(analysis, post)

    def _analyze_comments(self, post: SocialPost) -> List[Dict[str, Any]]:
        """Analyze comments - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._analyze_comments(post)

    def _analyze_media_content(
        self, media_urls: List[str]
    ) -> Dict[str, Any]:
        """Analyze media content - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._analyze_media_content(media_urls)

    def _deterministic_analysis(
        self, post: SocialPost, include_comments: bool, include_media: bool
    ) -> Dict[str, Any]:
        """Deterministic analysis for testing - delegate to original implementation"""
        from src.domain.analysis.analyzers.intelligent_content_analyzer import (
            IntelligentContentAnalyzer,
        )

        analyzer = IntelligentContentAnalyzer()
        return analyzer._deterministic_analysis(post, include_comments, include_media)

    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check with provider and cache metrics"""
        base_health = await super().health_check()

        # Add provider health
        provider_health_data = {
            name: health.to_dict()
            for name, health in self.provider_health.items()
        }

        # Add cache metrics
        cache_metrics = self.cache.get_metrics()

        # Add analysis metrics
        analysis_metrics = {
            "total_analyses": self.analysis_count,
            "total_batches": self.batch_count,
            "provider_rotations": self.provider_rotation_count,
            "cache_hit_rate": cache_metrics["hit_rate"],
        }

        base_health.update(
            {
                "provider_health": provider_health_data,
                "cache_metrics": cache_metrics,
                "analysis_metrics": analysis_metrics,
            }
        )

        return base_health

