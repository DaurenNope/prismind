import json
import logging
import re
from typing import Dict, Any
from langchain_core.messages import AIMessage
from src.domain.intelligence.agents.specialized.base_specialized import SpecializedAgent
import os
import google.generativeai as genai

logger = logging.getLogger(__name__)

class SkepticAgent(SpecializedAgent):
    """
    The Skeptic: Verifies claims and looks for contradictions.
    Provides structured JSON output with verification results.
    """
    def __init__(self):
        super().__init__(agent_id="skeptic", agent_name="The Skeptic", role="Verification")
        self._setup_ai()

    def _setup_ai(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash-lite")
        else:
            logger.warning("No Gemini API key found for Skeptic Agent")
            self.model = None

    async def _process_impl(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("🤨 Skeptic verifying content...")
        
        analysis_result = state.get("artifacts", {}).get("analysis_result", {})
        summary = analysis_result.get("summary", "")
        
        if not summary:
             return {
                "messages": [AIMessage(content="Skeptic: Nothing to verify.")],
                "current_agent": "skeptic"
            }

        verification = await self._verify_claims(summary)
        
        return {
            "messages": [AIMessage(content=f"Skeptic Report: {verification.get('verdict', 'Unknown')}")],
            "artifacts": {"verification_result": verification},
            "current_agent": "skeptic",
            "task_status": "verification_complete"
        }

    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check for Skeptic Agent"""
        base_health = await super().health_check()
        
        # Add agent-specific health
        agent_health = {
            **base_health,
            "model_available": self.model is not None,
            "last_verification": self.metrics.get("last_verification_time"),
            "verification_count": self.metrics.get("verification_count", 0),
        }
        
        return agent_health

    async def _verify_claims(self, text: str) -> Dict[str, Any]:
        """Verify claims with structured output"""
        if not self.model:
            return {
                "verdict": "AI unavailable",
                "trust_score": 0.0,
                "concerns": [],
                "reasoning": "Model not initialized"
            }

        prompt = f"""
Act as a skeptical fact-checker. Review the following:

"{text}"

Return JSON:
{{
    "verdict": "verified|questionable|false",
    "trust_score": 0-10,
    "concerns": ["concern1", "concern2"],
    "reasoning": "brief explanation"
}}

Return ONLY valid JSON.
"""

        try:
            import time
            start_time = time.time()
            response = self.model.generate_content(prompt)
            verification_time = time.time() - start_time
            
            text_resp = response.text.strip()

            # Extract JSON (handle markdown code blocks)
            if "```json" in text_resp:
                text_resp = text_resp.split("```json")[1].split("```")[0].strip()
            elif "```" in text_resp:
                text_resp = text_resp.split("```")[1].split("```")[0].strip()
            
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text_resp, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text_resp

            verification = json.loads(json_str)

            # Validate and normalize the response
            trust_score = float(verification.get("trust_score", 5.0))
            # Clamp trust_score to 0-10 range
            trust_score = max(0.0, min(10.0, trust_score))
            
            # Ensure concerns is a list
            concerns = verification.get("concerns", [])
            if not isinstance(concerns, list):
                concerns = [concerns] if concerns else []
            
            # Normalize verdict
            verdict = verification.get("verdict", "unknown").lower()
            valid_verdicts = ["verified", "questionable", "false", "unverified"]
            if verdict not in valid_verdicts:
                verdict = "unknown"
            
            structured_result = {
                "verdict": verdict,
                "trust_score": trust_score,
                "concerns": concerns,
                "reasoning": verification.get("reasoning", ""),
                "raw_response": response.text.strip()
            }
            
            # Update metrics
            self.metrics["last_verification_time"] = time.time()
            self.metrics["verification_count"] = self.metrics.get("verification_count", 0) + 1
            self.record_metric("verification_duration", verification_time)
            
            return structured_result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}, response: {text_resp[:200] if 'text_resp' in locals() else 'N/A'}")
            # Fallback to raw text
            return {
                "verdict": "error",
                "trust_score": 0.0,
                "concerns": [],
                "reasoning": "",
                "error": f"JSON parse error: {e}",
                "raw_response": text_resp if 'text_resp' in locals() else ""
            }
        except Exception as e:
            logger.error(f"Verification failed: {e}", exc_info=True)
            return {
                "verdict": "error",
                "trust_score": 0.0,
                "concerns": [],
                "reasoning": "",
                "error": str(e),
                "raw_response": text_resp if 'text_resp' in locals() else ""
            }
