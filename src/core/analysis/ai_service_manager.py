#!/usr/bin/env python3
"""
AI Service Manager for PrisMind
Manages initialization and configuration of AI services
"""

import os
from typing import List, Dict, Any
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
        ollama_url = os.getenv('OLLAMA_URL')
        if ollama_url:
            self.ai_services.append({
                'name': 'ollama',
                'url': ollama_url.rstrip('/'),
                'model': os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
            })
            print("✅ Ollama (Qwen) initialized")
        
        # 1. Mistral AI (Primary - best for analysis)
        mistral_key = os.getenv('MISTRAL_API_KEY')
        if mistral_key:
            self.ai_services.append({
                'name': 'mistral',
                'key': mistral_key,
                'base_url': 'https://api.mistral.ai/v1',
                'model': 'mistral-small-latest'
            })
            print("✅ Mistral AI initialized")
        
        # 2. Google Gemini (Secondary - best for vision)
        gemini_key = os.getenv('GEMINI_API_KEY')
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
            self.gemini_vision_model = genai.GenerativeModel('gemini-1.5-pro-vision-latest')
            self.ai_services.append({
                'name': 'gemini',
                'model': self.gemini_model,
                'vision_model': self.gemini_vision_model
            })
            print("✅ Google Gemini initialized")
        
        # 3. ShuttleAI (Fallback)
        if not self.ai_services:
            self.ai_services.append({'name': 'basic'})
            print("⚠️ No AI services available, using basic analysis")
    
    def get_available_services(self) -> List[Dict[str, Any]]:
        """Get list of available AI services"""
        return self.ai_services
    
    def get_service_by_name(self, name: str) -> Dict[str, Any]:
        """Get specific AI service by name"""
        for service in self.ai_services:
            if service.get('name') == name:
                return service
        return {}
    
    def has_service(self, name: str) -> bool:
        """Check if a specific service is available"""
        return any(service.get('name') == name for service in self.ai_services)
