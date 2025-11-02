#!/usr/bin/env python3
"""
Content Rewriter for Multi-Persona Publishing
Transforms discovered content into platform-optimized posts for different personas
"""

import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ContentRewriter:
    """
    Rewrites content for different personas and platforms
    
    Personas:
    - Technical Expert: Deep technical insights
    - Startup Builder: Practical applications
    - Learner/Educator: Teaching angle
    - Trendsetter: What's hot and why
    - Thought Leader: Big picture thinking
    
    Platforms:
    - Twitter/X: Short, punchy threads
    - LinkedIn: Professional insights
    - Blog: Long-form deep dives
    - Newsletter: Curated summaries
    """
    
    def __init__(self):
        self.personas = self._load_personas()
        self.ollama_url = "http://localhost:11434/api/generate"
    
    def _load_personas(self) -> Dict[str, Dict[str, Any]]:
        """Load persona templates"""
        
        return {
            "technical": {
                "name": "Technical Expert",
                "tone": "analytical, precise, code-focused",
                "audience": "senior developers, architects",
                "style": "Deep technical analysis with implementation details",
                "emoji": "🔧"
            },
            "builder": {
                "name": "Startup Builder",
                "tone": "pragmatic, action-oriented, efficient",
                "audience": "founders, product builders",
                "style": "Focus on practical applications and ROI",
                "emoji": "🚀"
            },
            "learner": {
                "name": "Learning Guide",
                "tone": "friendly, educational, accessible",
                "audience": "beginners, students, career switchers",
                "style": "Clear explanations with step-by-step guidance",
                "emoji": "📚"
            },
            "trendsetter": {
                "name": "Tech Trendsetter",
                "tone": "exciting, timely, culturally aware",
                "audience": "general tech community, early adopters",
                "style": "What's trending and why it matters now",
                "emoji": "🔥"
            },
            "thought_leader": {
                "name": "Thought Leader",
                "tone": "strategic, visionary, insightful",
                "audience": "executives, decision makers",
                "style": "Big picture implications and future trends",
                "emoji": "💡"
            }
        }
    
    async def rewrite_for_persona(
        self, 
        content: Dict[str, Any], 
        persona: str,
        platform: str = "twitter"
    ) -> Dict[str, Any]:
        """
        Rewrite content for specific persona and platform
        
        Args:
            content: Original content with analysis (from agents)
            persona: Persona ID (technical, builder, learner, etc.)
            platform: Target platform (twitter, linkedin, blog)
            
        Returns:
            Rewritten content optimized for persona and platform
        """
        
        if persona not in self.personas:
            return {"error": f"Unknown persona: {persona}"}
        
        persona_info = self.personas[persona]
        
        logger.info(f"✍️  Rewriting as {persona_info['name']} for {platform}")
        
        # Extract content info
        content_type = content.get("type", "article")
        
        if content_type == "github":
            return await self._rewrite_github(content, persona, platform, persona_info)
        elif content_type == "book":
            return await self._rewrite_book(content, persona, platform, persona_info)
        else:
            return await self._rewrite_article(content, persona, platform, persona_info)
    
    async def _rewrite_github(
        self, 
        content: Dict[str, Any], 
        persona: str,
        platform: str,
        persona_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Rewrite GitHub repo content"""
        
        # Get rewrite angle for this persona
        angles = content.get("rewrite_angles", [])
        persona_angle = next((a for a in angles if a["persona"] == persona), angles[0] if angles else {})
        
        # Build prompt
        prompt = f"""Rewrite this GitHub repository as a {persona_info['name']} for {platform}.

Repository: {content.get('name', '')}
Description: {content.get('description', '')}
Stars: {content.get('stars', 0):,}
TLDR: {content.get('tldr', '')}
Use Cases: {', '.join(content.get('use_cases', []))}
Key Features: {', '.join(content.get('key_features', []))}
Why Matters: {content.get('why_matters', '')}
Target Audience: {', '.join(content.get('target_audience', []))}

Angle: {persona_angle.get('angle', '')}
Hook: {persona_angle.get('hook', '')}

Write for:
- Tone: {persona_info['tone']}
- Audience: {persona_info['audience']}
- Style: {persona_info['style']}

Platform constraints:
{"- Thread format, 5-7 tweets, <280 chars each" if platform == "twitter" else ""}
{"- Professional tone, 150-200 words, actionable insights" if platform == "linkedin" else ""}

Rewritten post:"""

        result = await self._call_llm(prompt)
        
        return {
            "persona": persona,
            "persona_emoji": persona_info["emoji"],
            "platform": platform,
            "original_url": content.get("repo_url", ""),
            "rewritten_content": result,
            "angle_used": persona_angle.get("angle", ""),
            "hook": persona_angle.get("hook", ""),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _rewrite_book(
        self,
        content: Dict[str, Any],
        persona: str,
        platform: str,
        persona_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Rewrite book content"""
        
        # Get rewrite angle for this persona
        angles = content.get("rewrite_angles", [])
        persona_angle = next((a for a in angles if a["persona"] == persona), angles[0] if angles else {})
        
        prompt = f"""Rewrite this book insight as a {persona_info['name']} for {platform}.

Book: {content.get('title', '')} by {content.get('author', '')}
TLDR: {content.get('tldr', '')}
Key Concepts: {', '.join(content.get('key_concepts', [])[:5])}
Main Arguments: {', '.join(content.get('main_arguments', [])[:3])}
Applications: {', '.join(content.get('practical_applications', [])[:3])}

Angle: {persona_angle.get('angle', '')}
Hook: {persona_angle.get('hook', '')}

Write for:
- Tone: {persona_info['tone']}
- Audience: {persona_info['audience']}
- Style: {persona_info['style']}

Platform constraints:
{"- Thread format, 5-7 tweets, <280 chars each" if platform == "twitter" else ""}
{"- Professional tone, 150-200 words, actionable insights" if platform == "linkedin" else ""}

Rewritten post:"""

        result = await self._call_llm(prompt)
        
        return {
            "persona": persona,
            "persona_emoji": persona_info["emoji"],
            "platform": platform,
            "book_title": content.get("title", ""),
            "rewritten_content": result,
            "angle_used": persona_angle.get("angle", ""),
            "hook": persona_angle.get("hook", ""),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _rewrite_article(
        self,
        content: Dict[str, Any],
        persona: str,
        platform: str,
        persona_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Rewrite article/blog content"""
        
        prompt = f"""Rewrite this article as a {persona_info['name']} for {platform}.

Title: {content.get('title', '')}
Summary: {content.get('content_summary', content.get('content', '')[:300])}

Write for:
- Tone: {persona_info['tone']}
- Audience: {persona_info['audience']}
- Style: {persona_info['style']}

Platform constraints:
{"- Thread format, 5-7 tweets, <280 chars each" if platform == "twitter" else ""}
{"- Professional tone, 150-200 words, actionable insights" if platform == "linkedin" else ""}

Rewritten post:"""

        result = await self._call_llm(prompt)
        
        return {
            "persona": persona,
            "persona_emoji": persona_info["emoji"],
            "platform": platform,
            "original_url": content.get("url", ""),
            "rewritten_content": result,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """Call Ollama LLM"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": "qwen2.5:7b",
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": max_tokens
                        }
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "").strip()
                
                return "Error: Failed to generate content"
                
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Error: {e}"
    
    def get_available_personas(self) -> List[Dict[str, str]]:
        """Get list of available personas"""
        
        return [
            {
                "id": persona_id,
                "name": info["name"],
                "emoji": info["emoji"],
                "audience": info["audience"],
                "style": info["style"]
            }
            for persona_id, info in self.personas.items()
        ]
    
    async def generate_all_versions(
        self,
        content: Dict[str, Any],
        platform: str = "twitter"
    ) -> Dict[str, Dict[str, Any]]:
        """Generate versions for all personas"""
        
        logger.info(f"🎭 Generating all persona versions for {platform}")
        
        versions = {}
        
        for persona_id in self.personas.keys():
            rewritten = await self.rewrite_for_persona(content, persona_id, platform)
            versions[persona_id] = rewritten
        
        return versions


# Singleton
_rewriter = None


def get_rewriter() -> ContentRewriter:
    """Get global rewriter instance"""
    global _rewriter
    if _rewriter is None:
        _rewriter = ContentRewriter()
    return _rewriter


async def test_rewriter():
    """Test content rewriter"""
    
    print("🧪 Testing Content Rewriter\n")
    
    rewriter = get_rewriter()
    
    # Test GitHub content
    github_content = {
        "type": "github",
        "name": "openai/whisper",
        "description": "Robust Speech Recognition via Large-Scale Weak Supervision",
        "stars": 88865,
        "tldr": "State-of-the-art speech recognition with 99 language support",
        "use_cases": ["transcription", "subtitles", "voice interfaces", "accessibility"],
        "key_features": ["99 languages", "Multiple model sizes", "Easy to use", "Open source"],
        "why_matters": "Industry-leading solution • Excellent quality",
        "target_audience": ["developers", "data scientists"],
        "rewrite_angles": [
            {
                "persona": "technical",
                "angle": "Deep dive into architecture",
                "hook": "How Whisper achieves SOTA accuracy"
            },
            {
                "persona": "builder",
                "angle": "Practical applications",
                "hook": "5 ways to use Whisper in your products"
            }
        ]
    }
    
    # Test rewrite for builder persona
    print("✍️  Rewriting for: Startup Builder\n")
    
    result = await rewriter.rewrite_for_persona(github_content, "builder", "twitter")
    
    print("=" * 70)
    print(f"{result['persona_emoji']} {result['persona'].upper()} VERSION")
    print("=" * 70)
    print()
    print(result['rewritten_content'])
    print()
    print(f"Angle: {result['angle_used']}")
    print(f"Hook: {result['hook']}")
    print()
    print("✅ Rewriter working!")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_rewriter())
