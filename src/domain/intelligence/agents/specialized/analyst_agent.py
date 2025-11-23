import json
import logging
import re
from typing import Dict, Any, List
from langchain_core.messages import AIMessage
from src.agents.specialized.base_specialized import SpecializedAgent
from src.core.extraction.social_extractor_base import SocialPost
import os
import google.generativeai as genai

logger = logging.getLogger(__name__)

class AnalystAgent(SpecializedAgent):
    """
    The Analyst: Deep content understanding and entity extraction.
    Provides structured JSON output with comprehensive analysis.
    """
    def __init__(self):
        super().__init__(agent_id="analyst", agent_name="The Analyst", role="Deep Analysis")
        self._setup_ai()

    def _setup_ai(self):
        # Use Gemini for analysis as per existing stack
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash-lite") # Fast but capable
        else:
            logger.warning("No Gemini API key found for Analyst Agent")
            self.model = None

    async def _process_impl(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the content in the state.
        """
        logger.info("🧠 Analyst processing content...")
        
        # Extract content from state (assuming it's passed in artifacts or messages)
        # For now, let's assume the 'director' put the target post in artifacts
        target_post = state.get("artifacts", {}).get("current_post")
        
        if not target_post:
            return {
                "messages": [AIMessage(content="Analyst: No content found to analyze.")],
                "errors": ["No content provided"]
            }

        analysis = await self._analyze_content(target_post)
        
        return {
            "messages": [AIMessage(content=f"Analyst Report: {analysis.get('summary', 'No summary')}")],
            "artifacts": {"analysis_result": analysis},
            "current_agent": "analyst",
            "task_status": "analysis_complete"
        }

    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check for Analyst Agent"""
        base_health = await super().health_check()
        
        # Add agent-specific health
        agent_health = {
            **base_health,
            "model_available": self.model is not None,
            "last_analysis": self.metrics.get("last_analysis_time"),
            "analysis_count": self.metrics.get("analysis_count", 0),
        }
        
        return agent_health

    async def _analyze_content(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze content with structured output"""
        if not self.model:
            return {
                "summary": "AI not available",
                "entities": [],
                "value_score": 0.0,
                "key_concepts": [],
                "category": "unknown",
                "sentiment": "neutral",
                "error": "Model not initialized"
            }

        content = post.get("content", "") or post.get("title", "")
        if not content:
            return {
                "summary": "No content to analyze",
                "entities": [],
                "value_score": 0.0,
                "key_concepts": [],
                "category": "unknown",
                "sentiment": "neutral",
                "error": "No content provided"
            }

        prompt = f"""
Analyze the following content as an expert intelligence analyst.

Content:
{content}

Return JSON:
{{
    "summary": "2-3 sentence summary",
    "entities": ["entity1", "entity2"],
    "value_score": 0-10,
    "key_concepts": ["concept1", "concept2"],
    "category": "category name",
    "sentiment": "positive|negative|neutral"
}}

Return ONLY valid JSON, no additional text.
"""

        try:
            import time
            start_time = time.time()
            response = self.model.generate_content(prompt)
            analysis_time = time.time() - start_time
            
            text = response.text.strip()

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text

            analysis = json.loads(json_str)
            
            # Validate and normalize the response
            value_score = float(analysis.get("value_score", 0.0))
            # Clamp value_score to 0-10 range
            value_score = max(0.0, min(10.0, value_score))
            
            # Ensure entities and key_concepts are lists
            entities = analysis.get("entities", [])
            if not isinstance(entities, list):
                entities = [entities] if entities else []
            
            key_concepts = analysis.get("key_concepts", [])
            if not isinstance(key_concepts, list):
                key_concepts = [key_concepts] if key_concepts else []
            
            # Normalize sentiment
            sentiment = analysis.get("sentiment", "neutral").lower()
            if sentiment not in ["positive", "negative", "neutral"]:
                sentiment = "neutral"
            
            structured_result = {
                "summary": analysis.get("summary", ""),
                "entities": entities,
                "value_score": value_score,
                "key_concepts": key_concepts,
                "category": analysis.get("category", "unknown"),
                "sentiment": sentiment,
                "raw_response": response.text.strip()
            }
            
            # Update metrics
            self.metrics["last_analysis_time"] = time.time()
            self.metrics["analysis_count"] = self.metrics.get("analysis_count", 0) + 1
            self.record_metric("analysis_duration", analysis_time)

            return structured_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}, response: {text[:200]}")
            # Fallback to raw text
            return {
                "summary": text[:200] if len(text) > 200 else text,
                "entities": [],
                "value_score": 0.0,
                "key_concepts": [],
                "category": "unknown",
                "sentiment": "neutral",
                "error": f"JSON parse error: {e}",
                "raw_response": text
            }
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return {
                "summary": "Analysis failed",
                "entities": [],
                "value_score": 0.0,
                "key_concepts": [],
                "category": "unknown",
                "sentiment": "neutral",
                "error": str(e),
                "raw_response": text if 'text' in locals() else ""
            }
