#!/usr/bin/env python3
"""
AI Summarizer for PrisMind
Generates TLDR summaries using Ollama/Gemini
"""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AISummarizer:
    """Generate TLDR summaries of content"""
    
    def __init__(self):
        self.ollama_available = self._check_ollama()
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = httpx.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def summarize(self, content: str, url: str = "", max_length: int = 200) -> Optional[str]:
        """
        Generate TLDR summary of content
        
        Args:
            content: Full content text
            url: Optional URL for context
            max_length: Max summary length
            
        Returns:
            TLDR summary or None
        """
        if not content or len(content) < 50:
            return None
        
        # Try Ollama first
        if self.ollama_available:
            summary = self._summarize_ollama(content, max_length)
            if summary:
                return summary
        
        # Fallback to extractive summary
        return self._extractive_summary(content, max_length)
    
    def _summarize_ollama(self, content: str, max_length: int) -> Optional[str]:
        """Use Ollama for summarization"""
        try:
            # Truncate very long content
            truncated = content[:2000] if len(content) > 2000 else content
            
            prompt = f"""Provide a TLDR summary in 1-2 sentences (max {max_length} chars).
Focus on the main point and why it matters.

Content:
{truncated}

TLDR:"""
            
            response = httpx.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5:7b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 100
                    }
                },
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get("response", "").strip()
                
                # Clean up
                summary = summary.replace("TLDR:", "").strip()
                summary = summary.split("\n")[0]  # First line only
                
                # Truncate if needed
                if len(summary) > max_length:
                    summary = summary[:max_length-3] + "..."
                
                return summary if summary else None
                
        except Exception as e:
            logger.debug(f"Ollama summarization failed: {e}")
            return None
    
    def _extractive_summary(self, content: str, max_length: int) -> str:
        """Simple extractive summary (fallback)"""
        # Take first sentence or paragraph
        sentences = content.split(". ")
        
        if sentences:
            summary = sentences[0]
            if not summary.endswith("."):
                summary += "."
            
            # Truncate if too long
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            
            return summary
        
        # Last resort: just truncate
        return content[:max_length-3] + "..."
    
    def analyze_github_repo(self, metadata: Dict[str, Any]) -> str:
        """Generate TLDR for GitHub repo"""
        description = metadata.get("description", "")
        stars = metadata.get("stars", 0)
        language = metadata.get("language", "")
        why_matters = metadata.get("why_matters", "")
        
        # Build concise summary
        parts = []
        
        if description:
            parts.append(description[:120])
        
        if stars > 1000:
            parts.append(f"⭐ {stars:,} stars")
        
        if why_matters:
            parts.append(why_matters)
        
        summary = ". ".join(parts)
        
        # Truncate if needed
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        return summary


# Global instance
_summarizer = None


def get_summarizer() -> AISummarizer:
    """Get global summarizer instance"""
    global _summarizer
    if _summarizer is None:
        _summarizer = AISummarizer()
    return _summarizer


def test_summarizer():
    """Test summarization"""
    
    print("🧪 Testing AI Summarizer\n")
    
    summarizer = AISummarizer()
    
    # Test content
    content = """
    Claude 3.5 Sonnet has been released with major performance improvements. 
    The new model shows significant gains in reasoning and coding tasks, 
    outperforming previous versions by 30% on benchmarks. Anthropic has also 
    improved the context window and reduced latency. This is a major update 
    for developers building AI applications.
    """
    
    print("Content:")
    print(content.strip())
    print()
    
    summary = summarizer.summarize(content)
    print(f"TLDR: {summary}")
    print()
    
    # Test GitHub
    github_metadata = {
        "name": "whisper",
        "description": "Robust Speech Recognition via Large-Scale Weak Supervision",
        "stars": 88865,
        "language": "Python",
        "why_matters": "Most popular open-source speech recognition model"
    }
    
    github_tldr = summarizer.analyze_github_repo(github_metadata)
    print(f"GitHub TLDR: {github_tldr}")
    
    print("\n✅ Summarizer working!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_summarizer()
