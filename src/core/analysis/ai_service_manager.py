#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
AI Service Manager for BEYONDLINES
Manages initialization and configuration of AI services
"""

import os
from typing import Any, Dict, List

import google.generativeai as genai


class AIServiceManager:
    """Manages AI service initialization and configuration"""

    def __init__(self):
        self.ai_services: List[Dict[str, Any]] = []
        self.gemini_model = None
        self.gemini_vision_model = None
        self._init_ai_services()

    def _init_ai_services(self):
        """Initialize available AI services in order of preference"""

        # 0. Ollama (Local Qwen) — prefer when available for local-first analysis
        ollama_url = os.getenv("OLLAMA_URL")
        if ollama_url:
            self.ai_services.append(
                {
                    "name": "ollama",
                    "url": ollama_url.rstrip("/"),
                    "model": os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                }
            )
            logger.info("✅ Ollama (Qwen) initialized")

        # 1. Mistral AI (Primary - best for analysis)
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
            logger.info("✅ Mistral AI initialized")

        # 2. Google Gemini (Secondary - best for vision)
        # Using Gemini 2.5 Flash-Lite for best daily limits (1,000 RPD on Free Tier)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.5-flash-lite")
            self.gemini_vision_model = genai.GenerativeModel(
                "gemini-1.5-pro-vision-latest"
            )
            self.ai_services.append(
                {
                    "name": "gemini",
                    "model": self.gemini_model,
                    "vision_model": self.gemini_vision_model,
                }
            )
            logger.info("✅ Google Gemini initialized")

        # 3. ShuttleAI (Fallback)
        if not self.ai_services:
            self.ai_services.append({"name": "basic"})
            logger.warning("⚠️ No AI services available, using basic analysis")

    def get_available_services(self) -> List[Dict[str, Any]]:
        """Get list of available AI services"""
        return self.ai_services

    def get_service_by_name(self, name: str) -> Dict[str, Any]:
        """Get specific AI service by name"""
        for service in self.ai_services:
            if service.get("name") == name:
                return service
        return {}

    def has_service(self, name: str) -> bool:
        """Check if a specific service is available"""
        return any(service.get("name") == name for service in self.ai_services)

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        persona_id: str = "default",
    ) -> str:
        """Generate text using available AI services"""
        # Try services in order of preference
        for service in self.ai_services:
            try:
                if service["name"] == "ollama":
                    # Use Ollama for local generation
                    import httpx

                    response = httpx.post(
                        f"{service['url']}/api/generate",
                        json={
                            "model": service["model"],
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": temperature,
                                "num_predict": max_tokens,
                            },
                        },
                        timeout=30.0,
                    )
                    if response.status_code == 200:
                        return response.json().get("response", "").strip()

                elif service["name"] == "mistral":
                    # Use Mistral AI
                    import httpx

                    response = httpx.post(
                        f"{service['base_url']}/chat/completions",
                        json={
                            "model": service["model"],
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                        },
                        headers={"Authorization": f"Bearer {service['key']}"},
                        timeout=30.0,
                    )
                    if response.status_code == 200:
                        return response.json()["choices"][0]["message"][
                            "content"
                        ].strip()

                elif service["name"] == "gemini":
                    # Use Gemini
                    response = self.gemini_model.generate_content(prompt)
                    return response.text.strip()

            except Exception as e:
                logger.error(f"Error with {service['name']}: {e}")
                continue

        raise Exception("No AI services available for text generation")


# Global instance
ai_service_manager = AIServiceManager()
