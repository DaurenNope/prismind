#!/usr/bin/env python3
"""
Thread Summarizer (Simplified)
==============================

Main orchestrator for thread summarization using modular components.
"""

from typing import Dict, Any
from src.core.analysis.thread_summary import ThreadSummary
from src.core.analysis.thread_summarizer_ai import ThreadSummarizerAI
from src.core.analysis.thread_summarizer_parser import ThreadSummarizerParser


class ThreadSummarizer:
    """Main thread summarizer using modular components"""
    
    def __init__(self):
        self.ai_service = ThreadSummarizerAI()
        self.parser = ThreadSummarizerParser()
        print("🧵 Thread Summarizer initialized")
    
    def summarize_thread(self, content: str, author: str = "", platform: str = "") -> ThreadSummary:
        """
        Summarize a thread using available AI services
        
        Args:
            content: The thread content to summarize
            author: Author of the thread
            platform: Platform (twitter, reddit, etc.)
            
        Returns:
            ThreadSummary object with comprehensive summary
        """
        if not content or len(content.strip()) < 10:
            return self._create_empty_summary()
        
        print(f"🧵 Summarizing {platform} thread by {author}")
        
        # Try AI services in order of preference
        try:
            # Try Ollama first (local)
            if self.ai_service.ollama_url:
                result = self.ai_service.summarize_with_ollama(content, author, platform)
                if result.confidence > 0.5:
                    return result
            
            # Try Mistral
            if self.ai_service.mistral_key:
                result = self.ai_service.summarize_with_mistral(content, author, platform)
                if result.confidence > 0.5:
                    return result
            
            # Try Gemini
            if self.ai_service.gemini_key:
                result = self.ai_service.summarize_with_gemini(content, author, platform)
                if result.confidence > 0.5:
                    return result
        
        except Exception as e:
            print(f"⚠️ AI summarization failed: {e}")
        
        # Fallback to basic summarization
        return self.parser.basic_summarize(content, author, platform)
    
    def generate_summary_from_dict(self, post_data: Dict[str, Any]) -> ThreadSummary:
        """Generate summary from post data dictionary"""
        content = post_data.get('content', '')
        author = post_data.get('author', '')
        platform = post_data.get('platform', '')
        
        return self.summarize_thread(content, author, platform)
    
    def _create_empty_summary(self) -> ThreadSummary:
        """Create empty summary for invalid content"""
        return ThreadSummary(
            main_topic="No content",
            key_points=[],
            insights=[],
            sentiment="neutral",
            action_items=[],
            summary="No content to summarize",
            confidence=0.0,
            ai_service_used="none"
        )
