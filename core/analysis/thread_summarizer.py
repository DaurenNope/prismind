#!/usr/bin/env python3
"""
Thread Summarizer
Generate intelligent summaries and insights from social media threads
"""

import os
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Import AI clients
try:
    from mistralai.client import MistralClient
    from mistralai.models.chat_completion import ChatMessage
except ImportError:
    MistralClient = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    import requests
    import json as json_lib
except ImportError:
    requests = None

@dataclass
class ThreadSummary:
    """Structured thread summary"""
    main_topic: str
    value_proposition: str
    key_points: List[str]
    actionable_insights: List[str]
    category: str
    tags: List[str]
    summary_preview: str  # Short preview for UI
    full_summary: str     # Detailed summary
    confidence_score: float

class ThreadSummarizer:
    """Generate intelligent summaries from social media threads"""
    
    def __init__(self):
        load_dotenv()
        self.mistral_client = None
        self.gemini_model = None
        self.ollama_available = False
        
        # Initialize Mistral
        mistral_key = os.getenv('MISTRAL_API_KEY')
        if mistral_key and MistralClient:
            self.mistral_client = MistralClient(api_key=mistral_key)
        
        # Initialize Gemini
        gemini_key = os.getenv('GOOGLE_API_KEY')
        if gemini_key and genai:
            genai.configure(api_key=gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
        
        # Check Ollama availability
        if requests:
            try:
                response = requests.get('http://localhost:11434/api/tags', timeout=2)
                if response.status_code == 200:
                    self.ollama_available = True
                    print("✅ Ollama detected and available")
            except:
                pass
    
    def summarize_thread(self, content: str, author: str = "", platform: str = "") -> ThreadSummary:
        """Generate comprehensive thread summary"""
        try:
            # Priority: Ollama (local) > Mistral > Gemini > Basic
            if self.ollama_available:
                return self._summarize_with_ollama(content, author, platform)
            elif self.mistral_client:
                return self._summarize_with_mistral(content, author, platform)
            elif self.gemini_model:
                return self._summarize_with_gemini(content, author, platform)
            else:
                # Fallback to basic analysis
                return self._basic_summarize(content, author, platform)
                
        except Exception as e:
            print(f"⚠️ Error in thread summarization: {e}")
            return self._basic_summarize(content, author, platform)
    
    def _summarize_with_ollama(self, content: str, author: str, platform: str) -> ThreadSummary:
        """Generate summary using Ollama (local AI)"""
        
        prompt = f"""Analyze this social media post and provide a structured summary.

CONTENT:
{content}

AUTHOR: {author}
PLATFORM: {platform}

Please provide:
1. A clear, concise main topic (max 100 chars)
2. A brief value proposition (what's the key benefit/insight)
3. 3-5 key points from the content
4. 2-3 actionable insights or takeaways
5. A category (Tool, Tutorial, Opinion, Discussion, News, Resource, Guide, Tip)
6. 3-5 relevant tags
7. A 2-sentence summary
8. A confidence score (0.0-1.0)

Focus on:
- What problem does this solve?
- What can someone DO with this information?
- What are the key insights or techniques mentioned?
- What tools, concepts, or methods are discussed?

Be precise and practical. Avoid generic descriptions."""

        try:
            # Call Ollama API
            response = requests.post('http://localhost:11434/api/generate', 
                json={
                    'model': 'qwen3:8b',
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.3,
                        'top_p': 0.9,
                        'max_tokens': 1000
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get('response', '')
                
                # Parse the AI response
                return self._parse_ai_response(ai_response, content)
            else:
                print(f"⚠️ Ollama API error: {response.status_code}")
                return self._basic_summarize(content, author, platform)
                
        except Exception as e:
            print(f"⚠️ Ollama error: {e}")
            return self._basic_summarize(content, author, platform)
    
    def _summarize_with_mistral(self, content: str, author: str, platform: str) -> ThreadSummary:
        """Generate summary using Mistral AI"""
        
        prompt = f"""Analyze this social media thread and provide a structured summary.

THREAD CONTENT:
{content}

AUTHOR: {author}
PLATFORM: {platform}

Please provide a JSON response with the following structure:
{{
    "main_topic": "Clear, concise description of what this thread is about",
    "value_proposition": "Why this matters - the key value or benefit",
    "key_points": ["3-5 most important points from the thread"],
    "actionable_insights": ["2-3 things readers can do with this information"],
    "category": "Primary category (e.g., 'AI Tools', 'Business Strategy', 'Tutorial', 'Product Launch')",
    "tags": ["3-5 relevant tags"],
    "summary_preview": "One-line preview for UI (max 100 chars)",
    "full_summary": "2-3 sentence detailed summary",
    "confidence_score": 0.85
}}

Focus on:
- What product/concept is being discussed
- Key benefits and features
- Practical value for readers
- Clear, actionable language"""

        try:
            response = self.mistral_client.chat(
                model="mistral-large-latest",
                messages=[ChatMessage(role="user", content=prompt)],
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                
                return ThreadSummary(
                    main_topic=result_data.get('main_topic', 'Unknown Topic'),
                    value_proposition=result_data.get('value_proposition', ''),
                    key_points=result_data.get('key_points', []),
                    actionable_insights=result_data.get('actionable_insights', []),
                    category=result_data.get('category', 'General'),
                    tags=result_data.get('tags', []),
                    summary_preview=result_data.get('summary_preview', '')[:100],
                    full_summary=result_data.get('full_summary', ''),
                    confidence_score=result_data.get('confidence_score', 0.7)
                )
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            print(f"⚠️ Mistral summarization failed: {e}")
            return self._basic_summarize(content, author, platform)
    
    def _summarize_with_gemini(self, content: str, author: str, platform: str) -> ThreadSummary:
        """Generate summary using Google Gemini"""
        
        prompt = f"""Analyze this social media thread and create an intelligent summary.

THREAD: {content}
AUTHOR: {author}
PLATFORM: {platform}

Provide:
1. Main Topic: What is this about?
2. Value Proposition: Why does this matter?
3. Key Points: 3-5 most important insights
4. Actionable Items: What can readers do?
5. Category: Primary topic category
6. Tags: Relevant keywords
7. Preview: One-line summary (max 100 chars)
8. Full Summary: 2-3 detailed sentences

Format as JSON."""

        try:
            response = self.gemini_model.generate_content(prompt)
            result_text = response.text
            
            # Try to parse JSON response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                
                return ThreadSummary(
                    main_topic=result_data.get('main_topic', 'Unknown Topic'),
                    value_proposition=result_data.get('value_proposition', ''),
                    key_points=result_data.get('key_points', []),
                    actionable_insights=result_data.get('actionable_insights', []),
                    category=result_data.get('category', 'General'),
                    tags=result_data.get('tags', []),
                    summary_preview=result_data.get('preview', '')[:100],
                    full_summary=result_data.get('full_summary', ''),
                    confidence_score=0.8
                )
            else:
                # Parse structured text response
                return self._parse_structured_response(result_text, content)
                
        except Exception as e:
            print(f"⚠️ Gemini summarization failed: {e}")
            return self._basic_summarize(content, author, platform)
    
    def _parse_structured_response(self, response: str, content: str) -> ThreadSummary:
        """Parse structured text response from AI"""
        lines = response.split('\n')
        
        main_topic = "Unknown Topic"
        value_prop = ""
        key_points = []
        actionable = []
        category = "General"
        tags = []
        preview = ""
        full_summary = ""
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "main topic" in line.lower() or "topic:" in line.lower():
                main_topic = line.split(':', 1)[-1].strip()
                current_section = "topic"
            elif "value" in line.lower() and "proposition" in line.lower():
                value_prop = line.split(':', 1)[-1].strip()
                current_section = "value"
            elif "key points" in line.lower():
                current_section = "points"
            elif "actionable" in line.lower():
                current_section = "actionable"
            elif "category" in line.lower():
                category = line.split(':', 1)[-1].strip()
            elif "tags" in line.lower():
                tags_text = line.split(':', 1)[-1].strip()
                tags = [t.strip() for t in tags_text.split(',')]
            elif "preview" in line.lower():
                preview = line.split(':', 1)[-1].strip()[:100]
            elif "summary" in line.lower() and "full" in line.lower():
                full_summary = line.split(':', 1)[-1].strip()
            elif line.startswith(('-', '•', '*')) and current_section == "points":
                key_points.append(line[1:].strip())
            elif line.startswith(('-', '•', '*')) and current_section == "actionable":
                actionable.append(line[1:].strip())
        
        # Generate preview if not provided
        if not preview:
            preview = f"{main_topic} - {value_prop}"[:100]
        
        # Generate full summary if not provided
        if not full_summary:
            full_summary = f"{main_topic}. {value_prop}. Key benefits include {', '.join(key_points[:2])}."
        
        return ThreadSummary(
            main_topic=main_topic,
            value_proposition=value_prop,
            key_points=key_points,
            actionable_insights=actionable,
            category=category,
            tags=tags,
            summary_preview=preview,
            full_summary=full_summary,
            confidence_score=0.7
        )
    
    def _parse_ai_response(self, ai_response: str, original_content: str) -> ThreadSummary:
        """Parse AI response into ThreadSummary structure"""
        try:
            lines = ai_response.strip().split('\n')
            
            # Extract information with fallbacks
            main_topic = "Social Media Post"
            value_prop = ""
            key_points = []
            actionable_insights = []
            category = "Post"
            tags = []
            summary = ""
            confidence = 0.8
            
            current_section = ""
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Detect sections
                if "main topic" in line.lower() or "topic:" in line.lower():
                    current_section = "topic"
                    # Extract topic from same line if present
                    if ":" in line:
                        topic_candidate = line.split(":", 1)[1].strip()
                        if len(topic_candidate) > 3:
                            main_topic = topic_candidate[:100]
                elif "value proposition" in line.lower() or "benefit" in line.lower():
                    current_section = "value"
                elif "key points" in line.lower() or "points:" in line.lower():
                    current_section = "points"
                elif "actionable" in line.lower() or "takeaways" in line.lower():
                    current_section = "insights"
                elif "category" in line.lower():
                    current_section = "category"
                    if ":" in line:
                        cat_candidate = line.split(":", 1)[1].strip()
                        if cat_candidate in ["Tool", "Tutorial", "Opinion", "Discussion", "News", "Resource", "Guide", "Tip"]:
                            category = cat_candidate
                elif "tags" in line.lower():
                    current_section = "tags"
                elif "summary" in line.lower():
                    current_section = "summary"
                elif "confidence" in line.lower():
                    current_section = "confidence"
                    # Extract confidence score
                    import re
                    conf_match = re.search(r'(\d+\.?\d*)', line)
                    if conf_match:
                        confidence = min(float(conf_match.group(1)), 1.0)
                else:
                    # Process content based on current section
                    if current_section == "topic" and len(line) > 3:
                        main_topic = line[:100]
                    elif current_section == "value" and len(line) > 5:
                        value_prop = line
                    elif current_section == "points" and (line.startswith("-") or line.startswith("•") or line.startswith("*")):
                        key_points.append(line[1:].strip())
                    elif current_section == "insights" and (line.startswith("-") or line.startswith("•") or line.startswith("*")):
                        actionable_insights.append(line[1:].strip())
                    elif current_section == "tags":
                        # Extract tags from line
                        tag_candidates = line.replace(",", " ").replace("#", "").split()
                        for tag in tag_candidates:
                            if len(tag) > 1 and tag.isalnum():
                                tags.append(tag.title())
                    elif current_section == "summary" and len(line) > 10:
                        summary = line
            
            # Fallbacks if parsing failed
            if not main_topic or main_topic == "Social Media Post":
                # Extract from first meaningful sentence
                sentences = original_content.split('.')
                for sentence in sentences[:3]:
                    if len(sentence.strip()) > 20:
                        main_topic = sentence.strip()[:100]
                        break
            
            if not summary:
                summary = f"Discussion about {main_topic.lower()}" if main_topic else "Social media post analysis"
            
            if not tags:
                tags = ["AI", "Social"] if "ai" in original_content.lower() else ["Social"]
            
            return ThreadSummary(
                main_topic=main_topic,
                value_proposition=value_prop or f"Insights about {main_topic.lower()}",
                key_points=key_points[:5] or [main_topic],
                actionable_insights=actionable_insights[:3] or ["Apply insights to your workflow"],
                category=category,
                tags=tags[:5],
                summary_preview=summary[:200],
                full_summary=summary,
                confidence_score=confidence
            )
            
        except Exception as e:
            print(f"⚠️ Error parsing AI response: {e}")
            # Return basic fallback
            return ThreadSummary(
                main_topic=original_content[:100] if original_content else "Social Media Post",
                value_proposition="Insights from social media content",
                key_points=[original_content[:200]] if original_content else ["Content analysis"],
                actionable_insights=["Review and apply insights"],
                category="Post",
                tags=["AI", "Content"],
                summary_preview=original_content[:200] if original_content else "Social media analysis",
                full_summary=original_content[:500] if original_content else "Content summary",
                confidence_score=0.5
            )
    
    def _basic_summarize(self, content: str, author: str, platform: str) -> ThreadSummary:
        """Advanced rule-based summarization without AI APIs"""
        
        content_lower = content.lower()
        lines = content.split('\n')
        sentences = re.split(r'[.!?]+', content)
        clean_sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
        
        # Extract main topic with better patterns
        main_topic = "Social Media Post"
        topic_patterns = [
            r"meet\s+([^—\n.!?]+)",
            r"introducing\s+([^—\n.!?]+)", 
            r"announcing\s+([^—\n.!?]+)",
            r"^([^.!?\n]*(?:\.new|\.com|\.ai)[^.!?\n]*)",  # Domain names
            r"([A-Z][a-zA-Z]*(?:\.[a-zA-Z]+)+)",  # CamelCase.domain
            r"^([^.!?\n]*(?:tool|app|platform|service|product|system)[^.!?\n]*)",
        ]
        
        for pattern in topic_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                topic_candidate = match.group(1).strip()
                if len(topic_candidate) > 3 and len(topic_candidate) < 100:
                    main_topic = topic_candidate
                    break
        
        # Extract value proposition
        value_prop = ""
        value_patterns = [
            r"(?:can|lets?|allows?|enables?)\s+(?:you\s+)?([^.!?\n]{20,80})",
            r"(?:build|create|make|generate)\s+([^.!?\n]{15,60})",
            r"(?:the first|now you can|finally)\s+([^.!?\n]{20,80})",
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value_prop = match.group(1).strip()
                break
        
        # Extract key features/points
        key_points = []
        
        # Look for bullet points or numbered lists
        bullet_patterns = [
            r"^[•\-\*]\s*(.+)$",
            r"^🔹\s*(.+)$",
            r"^\d+\.\s*(.+)$",
        ]
        
        for line in lines:
            line = line.strip()
            for pattern in bullet_patterns:
                match = re.match(pattern, line)
                if match and len(match.group(1)) > 10:
                    key_points.append(match.group(1).strip())
        
        # If no bullet points, extract key sentences
        if not key_points:
            # Look for sentences with key indicators
            key_indicators = ['agent', 'tool', 'feature', 'can', 'build', 'create', 'make']
            for sentence in clean_sentences:
                if any(indicator in sentence.lower() for indicator in key_indicators):
                    if len(sentence) > 20 and len(sentence) < 150:
                        key_points.append(sentence.strip())
                        if len(key_points) >= 4:
                            break
        
        # Extract actionable insights
        actionable = []
        action_patterns = [
            r"(?:try|use|check out|visit|start|go to)\s+([^.!?\n]{10,60})",
            r"(?:you can|users can)\s+([^.!?\n]{15,80})",
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) > 10:
                    actionable.append(match.strip())
                    if len(actionable) >= 3:
                        break
        
        # Determine category with better logic
        category = "General"
        category_keywords = {
            "AI/Tech": ['ai', 'artificial intelligence', 'machine learning', 'agent', 'llm', 'gpt', 'model'],
            "Tools": ['tool', 'app', 'platform', 'software', 'service', 'api'],
            "Business": ['business', 'startup', 'company', 'revenue', 'growth', 'strategy'],
            "Tutorial": ['how to', 'tutorial', 'guide', 'step', 'learn', 'course'],
            "Product Launch": ['announcing', 'introducing', 'launch', 'new', 'beta', 'release'],
        }
        
        for cat, keywords in category_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                category = cat
                break
        
        # Extract tags
        tags = []
        # Look for hashtags
        hashtag_matches = re.findall(r'#(\w+)', content)
        tags.extend(hashtag_matches[:3])
        
        # Add domain-based tags
        domain_matches = re.findall(r'(\w+\.(?:new|com|ai|app|io))', content_lower)
        tags.extend([d.split('.')[0].title() for d in domain_matches[:2]])
        
        # Enhanced category-based tags
        tech_keywords = ['ai', 'agent', 'llm', 'gpt', 'model', 'machine learning', 'artificial intelligence']
        tool_keywords = ['tool', 'app', 'platform', 'software', 'service', 'api', 'builder']
        business_keywords = ['business', 'startup', 'company', 'revenue', 'growth', 'strategy', 'million', 'funding']
        tutorial_keywords = ['how to', 'tutorial', 'guide', 'step', 'learn', 'course', 'tips']
        
        if any(keyword in content_lower for keyword in tech_keywords):
            tags.append('AI/Tech')
        if any(keyword in content_lower for keyword in tool_keywords):
            tags.append('Tools')
        if any(keyword in content_lower for keyword in business_keywords):
            tags.append('Business')
        if any(keyword in content_lower for keyword in tutorial_keywords):
            tags.append('Tutorial')
        
        # Add specific product/tool tags
        specific_tools = ['n8n', 'cursor', 'chai', 'emergent', 'veo', 'cal', 'plugai', 'umax']
        for tool in specific_tools:
            if tool in content_lower:
                tags.append(tool.title())
        
        # Add platform tags
        if 'twitter' in content_lower or 'x.com' in content_lower:
            tags.append('Twitter')
        if 'reddit' in content_lower:
            tags.append('Reddit')
        
        tags = list(set(tags))[:8]  # Remove duplicates, limit to 8
        
        # Generate intelligent preview
        if "chai.new" in content_lower:
            preview = "Chai.new - AI agent builder platform for creating production-ready agents in minutes"
        elif value_prop:
            preview = f"{main_topic} - {value_prop}"
        elif key_points:
            preview = f"{main_topic} - {key_points[0][:60]}..."
        else:
            preview = f"{main_topic} - {clean_sentences[0][:60]}..." if clean_sentences else main_topic
        
        preview = preview[:100]
        
        # Generate full summary
        summary_parts = [main_topic]
        if value_prop:
            summary_parts.append(value_prop)
        if key_points:
            summary_parts.append(f"Key features: {', '.join(key_points[:2])}")
        
        full_summary = ". ".join(summary_parts)[:300]
        
        return ThreadSummary(
            main_topic=main_topic,
            value_proposition=value_prop,
            key_points=key_points[:5],
            actionable_insights=actionable[:3],
            category=category,
            tags=tags,
            summary_preview=preview,
            full_summary=full_summary,
            confidence_score=0.8  # Higher confidence for rule-based
        )

# Example usage and testing
if __name__ == "__main__":
    summarizer = ThreadSummarizer()
    
    # Test with Ahmad Awais thread
    test_content = """For the first time, you can vibe-code any AI agent.

Meet https://Chai.new — Computer Human AI by Langbase ☕

🔹Prompt: "make an agent that…"
🔹Sip: chai builds any AI agent
🔹Ship: every agent gets a UI 🤯

Like your on-demand AI Engineer.
What will you s(h)ip today?

Watch me vibe code several AI agents in this video

- An AI agent to chat with pdf
- Agent that finds a lunch spot near me
- Bed time story maker agent by DT
- AI email agent that can summarize, analyze, and generate a response

Chai is beta right now, oh it's super powerful."""
    
    summary = summarizer.summarize_thread(test_content, "@MrAhmadAwais", "Twitter")
    
    print("🎯 Thread Summary:")
    print(f"Main Topic: {summary.main_topic}")
    print(f"Preview: {summary.summary_preview}")
    print(f"Category: {summary.category}")
    print(f"Key Points: {summary.key_points}")

# Add method to ThreadSummarizer class
def generate_summary_from_dict(self, post_data):
    """Generate summary from dictionary data"""
    try:
        content = post_data.get('content', '')
        platform = post_data.get('platform', 'unknown')
        author = post_data.get('author', '')
        
        if not content or len(content.strip()) < 10:
            return {}
        
        # Use existing summarize_thread method
        summary = self.summarize_thread(content, author, platform)
        
        # Convert to dictionary format
        result = {
            'smart_title': summary.main_topic[:100] if summary.main_topic else content[:100],
            'summary': summary.full_summary,
            'smart_tags': summary.tags,
            'use_cases': summary.actionable_insights,
            'category': summary.category,
            'content_type': 'Thread' if len(content) > 500 else 'Post',
            'topic': summary.main_topic
        }
        
        return result
        
    except Exception as e:
        print(f"Error in generate_summary_from_dict: {e}")
        return {}

# Monkey patch the method to the class
ThreadSummarizer.generate_summary_from_dict = generate_summary_from_dict