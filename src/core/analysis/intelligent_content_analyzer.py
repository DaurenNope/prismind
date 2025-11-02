"""
PrisMind Intelligent Content Analyzer
=====================================

This is the core intelligence system that makes PrisMind truly smart.
It analyzes not just the original post, but also:
- The most valuable comments and discussions
- Media content (images, videos) using AI vision
- Extracts actionable insights and learning points
- Provides sophisticated value scoring

Author: PrisMind AI System
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

# AI imports
import google.generativeai as genai
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Core imports
from src.core.extraction.social_extractor_base import SocialPost


class IntelligentContentAnalyzer:
    """The brain of PrisMind - provides deep analysis of social media content"""
    
    def __init__(self):
        """Initialize the intelligent analyzer with multiple AI backends"""
        
        # Initialize sentiment analyzer
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Initialize AI services (try multiple for redundancy)
        self.ai_services = []
        self._init_ai_services()
        
        print(f"🧠 Intelligent Content Analyzer initialized with {len(self.ai_services)} AI services")
    
    def _init_ai_services(self):
        """Initialize available AI services in order of preference"""

        # 0. Ollama (Local Qwen) — prefer when available for local-first analysis
        ollama_url = os.getenv('OLLAMA_URL')
        if ollama_url:
            self.ai_services.append({
                'name': 'ollama',
                'url': ollama_url.rstrip('/'),
                'model': os.getenv('OLLAMA_MODEL', 'qwen2.5:1.5b'),
                'options': {
                    'num_predict': 150,  # Limit for speed
                    'temperature': 0.3
                }
            })
            print("✅ Ollama (Qwen 1.5B - Fast) initialized")

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
    
    async def analyze_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze content data and provide insights.
        
        This method is a wrapper around analyze_bookmark for backward compatibility.
        
        Args:
            content_data: Dictionary containing content information
            
        Returns:
            Analysis results
        """
        # Create a minimal SocialPost object from the content data
        post = SocialPost(
            post_id=content_data.get("post_id", ""),
            platform=content_data.get("platform", "unknown"),
            content=content_data.get("content", ""),
            author=content_data.get("author", ""),
            author_handle=content_data.get("author_handle", ""),
            url=content_data.get("url", ""),
            created_at=content_data.get("created_at", datetime.now().isoformat()),
            hashtags=content_data.get("hashtags", []),
            engagement=content_data.get("engagement", {}),
            media_urls=content_data.get("media_urls", []),
            post_type=content_data.get("post_type", "text")
        )
        
        # Analyze the post using the existing analyze_bookmark method
        return self.analyze_bookmark(post)
    
    def analyze_bookmark(self, post: SocialPost, include_comments: bool = True, include_media: bool = True) -> Dict[str, Any]:
        """Analyze a bookmark with AI services, with timeout and error handling"""
        
        print(f"🔍 Analyzing {post.platform} post: {post.post_id}")

        # Deterministic mode for testing and reproducibility
        if os.getenv('DETERMINISTIC_ANALYSIS', '0') == '1':
            return self._deterministic_analysis(post, include_comments=include_comments, include_media=include_media)
        
        analysis = {
            'post_id': post.post_id,
            'platform': post.platform,
            'analyzed_at': datetime.now().isoformat(),
            'analysis_version': '2.0'
        }
        
        # 1. Core Content Analysis
        try:
            core_analysis = self._analyze_core_content(post)
            analysis.update(core_analysis)
        except Exception as e:
            print(f"⚠️ Core content analysis failed: {e}")
            # Use basic analysis as fallback
            core_analysis = self._basic_analysis(post, self.sentiment_analyzer.polarity_scores(post.content or ""))
            analysis.update(core_analysis)
        
        # 2. Comment Analysis (Reddit only)
        if include_comments and post.platform == 'reddit':
            try:
                comment_analysis = self._analyze_comments(post)
                analysis['comment_insights'] = comment_analysis
            except Exception as e:
                print(f"⚠️ Comment analysis failed: {e}")
                analysis['comment_insights'] = []
        
        # 3. Media Analysis
        if include_media and post.media_urls:
            try:
                media_analysis = self._analyze_media_content(post.media_urls)
                analysis['media_insights'] = media_analysis

                # Enhance analysis with media insights
                if media_analysis.get('analyzed_media', 0) > 0:
                    for insight in media_analysis.get('insights', []):
                        # Add technical concepts from images
                        if 'technical_concepts' in insight and insight['technical_concepts']:
                            existing_concepts = analysis.get('key_concepts', [])
                            for concept in insight['technical_concepts']:
                                if concept not in existing_concepts:
                                    existing_concepts.append(concept)
                            analysis['key_concepts'] = existing_concepts

                        # Flag high-value visual content
                        if insight.get('educational_value') == 'high' and insight.get('adds_value') == 'yes':
                            analysis['has_high_value_visuals'] = True

                        # Add extracted text to context
                        if insight.get('extracted_text'):
                            analysis['visual_text_content'] = insight['extracted_text']

            except Exception as e:
                print(f"⚠️ Media analysis failed: {e}")
                analysis['media_insights'] = {
                    'total_media': len(post.media_urls),
                    'analyzed_media': 0,
                    'insights': []
                }
        
        # 4. Advanced Value Scoring
        try:
            value_score = self._calculate_intelligent_value_score(analysis, post)
            analysis['intelligent_value_score'] = value_score
        except Exception as e:
            print(f"⚠️ Value scoring failed: {e}")
            analysis['intelligent_value_score'] = 0.0
        
        # 5. Content Quality Score
        try:
            content_quality_score = self._calculate_content_quality_score(analysis, post)
            analysis['content_quality_score'] = content_quality_score
        except Exception as e:
            print(f"⚠️ Quality scoring failed: {e}")
            analysis['content_quality_score'] = 0.0
        
        # 6. Rewrite Candidate Assessment
        try:
            is_rewrite_candidate = self._determine_rewrite_candidate(analysis, post, content_quality_score)
            analysis['is_rewrite_candidate'] = is_rewrite_candidate
        except Exception as e:
            print(f"⚠️ Rewrite candidate assessment failed: {e}")
            analysis['is_rewrite_candidate'] = False
        
        # 7. Generate Actionable Insights
        try:
            actionable_insights = self._generate_actionable_insights(analysis, post)
            analysis['actionable_insights'] = actionable_insights
        except Exception as e:
            print(f"⚠️ Actionable insights generation failed: {e}")
            analysis['actionable_insights'] = []
        
        # 8. Learning Recommendations
        try:
            learning_recs = self._generate_learning_recommendations(analysis, post)
            analysis['learning_recommendations'] = learning_recs
        except Exception as e:
            print(f"⚠️ Learning recommendations generation failed: {e}")
            analysis['learning_recommendations'] = []
        
        print(f"✅ Analysis complete - Value Score: {analysis.get('intelligent_value_score', 0.0)}/10")
        return analysis

    def _deterministic_analysis(self, post: SocialPost, include_comments: bool, include_media: bool) -> Dict[str, Any]:
        """Produce stable, reproducible analysis without external AI calls.

        Uses simple rules and content hashing to generate consistent outputs for tests.
        """
        import hashlib

        content = post.content or ""
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        category_pool = ["Technology", "AI", "Business", "Learning", "General"]
        category = category_pool[int(content_hash[:2], 16) % len(category_pool)]

        sentiment_scores = self.sentiment_analyzer.polarity_scores(content)

        # Deterministic rewrite angles based on content hash
        personas = ["technical", "builder", "learner", "trendsetter", "thought_leader"]
        deterministic_rewrite_angles = []
        for i, persona in enumerate(personas):
            engagement_level = ["high", "medium", "low"][int(content_hash[i], 16) % 3]
            deterministic_rewrite_angles.append({
                "persona": persona,
                "angle": f"Deterministic {persona} angle for {category}",
                "hook": f"Consistent hook for {persona} persona",
                "key_points": [f"Point 1 for {persona}", f"Point 2 for {persona}", f"Point 3 for {persona}"],
                "target_audience": f"{persona.title()} audience",
                "estimated_engagement": engagement_level
            })

        # Calculate content age
        try:
            created_dt = datetime.fromisoformat(post.created_at.replace('Z', '+00:00'))
            age_hours = (datetime.now(created_dt.tzinfo) - created_dt).total_seconds() / 3600
            if age_hours < 24:
                publication_age = f"{int(age_hours)} hours"
            elif age_hours < 168:  # 7 days
                publication_age = f"{int(age_hours/24)} days"
            else:
                publication_age = f"{int(age_hours/168)} weeks"
        except Exception:
            publication_age = "unknown"

        analysis = {
            'post_id': post.post_id,
            'platform': post.platform,
            'analyzed_at': datetime.now().isoformat(),
            'analysis_version': 'deterministic-1.0',
            'category': category,
            'subcategory': post.platform.title(),
            'content_type': post.post_type,
            'topics': post.hashtags[:3] if post.hashtags else ['general'],
            'key_concepts': [],
            'summary': content[:200] + '...' if len(content) > 200 else content,
            'why_valuable': 'User bookmarked this content',
            'sentiment': 'Positive' if sentiment_scores['compound'] > 0.2 else ('Negative' if sentiment_scores['compound'] < -0.2 else 'Neutral'),
            'complexity_level': 'Unknown',
            'time_to_consume': 'Unknown',
            'actionable_items': [],
            'learning_value': 'Reproducible deterministic analysis',
            'practical_applications': [],
            'related_skills': [],
            'follow_up_research': [],
            'quality_indicators': [],
            'tags': post.hashtags[:5] if post.hashtags else [],
            'confidence_score': 1.0,
            'sentiment_scores': sentiment_scores,
            'ai_service': 'deterministic',
            'rewrite_angles': deterministic_rewrite_angles,
            'discovery_signals': {
                'author_authority': ['high', 'medium', 'low'][int(content_hash[5], 16) % 3],
                'trend_relevance': ['emerging', 'mainstream', 'declining'][int(content_hash[6], 16) % 3],
                'viral_potential': int(content_hash[7], 16) * 6,  # 0-90 range
                'discussion_quality': ['high', 'medium', 'low'][int(content_hash[8], 16) % 3],
                'unique_perspective': 'yes' if int(content_hash[9], 16) % 2 == 0 else 'no'
            },
            'content_freshness': {
                'publication_age': publication_age,
                'still_relevant': 'yes' if int(content_hash[10], 16) % 2 == 0 else 'no',
                'time_sensitivity': ['urgent', 'timely', 'evergreen'][int(content_hash[11], 16) % 3]
            }
        }

        try:
            value_score = self._calculate_intelligent_value_score(analysis, post)
            analysis['intelligent_value_score'] = value_score
        except Exception:
            analysis['intelligent_value_score'] = 5.0

        # Add content quality score and rewrite candidate assessment
        try:
            content_quality_score = self._calculate_content_quality_score(analysis, post)
            analysis['content_quality_score'] = content_quality_score
        except Exception:
            analysis['content_quality_score'] = 5.0

        try:
            is_rewrite_candidate = self._determine_rewrite_candidate(analysis, post, content_quality_score)
            analysis['is_rewrite_candidate'] = is_rewrite_candidate
        except Exception:
            analysis['is_rewrite_candidate'] = False

        if include_comments and post.platform == 'reddit':
            analysis['comment_insights'] = []
        if include_media and post.media_urls:
            analysis['media_insights'] = {
                'total_media': len(post.media_urls),
                'analyzed_media': 0,
                'insights': []
            }
        try:
            analysis['actionable_insights'] = self._generate_actionable_insights(analysis, post)
        except Exception:
            analysis['actionable_insights'] = []
        try:
            analysis['learning_recommendations'] = self._generate_learning_recommendations(analysis, post)
        except Exception:
            analysis['learning_recommendations'] = []
        return analysis
    
    def _analyze_core_content(self, post: SocialPost) -> Dict[str, Any]:
        """Analyze the main post content with AI"""
        
        # Get sentiment analysis
        sentiment_scores = self.sentiment_analyzer.polarity_scores(post.content)
        
        # Create comprehensive analysis prompt
        prompt = self._create_analysis_prompt(post)
        
        # Try AI services in order
        for service in self.ai_services:
            try:
                if service['name'] == 'ollama':
                    return self._analyze_with_ollama(prompt, sentiment_scores, service)
                elif service['name'] == 'mistral':
                    return self._analyze_with_mistral(prompt, sentiment_scores, service)
                elif service['name'] == 'gemini':
                    return self._analyze_with_gemini(prompt, sentiment_scores, service)
                else:
                    return self._basic_analysis(post, sentiment_scores)
            except Exception as e:
                print(f"⚠️ {service['name']} analysis failed: {e}")
                continue
        
        # Fallback to basic analysis
        return self._basic_analysis(post, sentiment_scores)
    
    def _create_analysis_prompt(self, post: SocialPost) -> str:
        """Create a comprehensive analysis prompt with improved categorization"""

        # Define specific categories to avoid generic "Technology" or "General"
        categories = [
            "AI & Machine Learning",
            "Development Tools",
            "Crypto & Web3",
            "Business & Startups",
            "Content Creation",
            "Automation & Productivity",
            "Coding & Software Engineering",
            "Data & Analytics",
            "Design & UX",
            "News & Trends",
            "Learning & Education",
            "Other"
        ]

        # Define the 5 personas for content transformation
        personas = ["technical", "builder", "learner", "trendsetter", "thought_leader"]

        return f"""
        Analyze this social media bookmark with deep intelligence and provide actionable insights:

        PLATFORM: {post.platform}
        AUTHOR: {post.author} ({post.author_handle})
        CONTENT: {post.content}
        HASHTAGS: {', '.join(post.hashtags) if post.hashtags else 'None'}
        ENGAGEMENT: {post.engagement}
        CREATED: {post.created_at}
        URL: {post.url}

        CATEGORIZATION RULES:
        - Choose ONE category from: {', '.join(categories)}
        - Be SPECIFIC - never use generic "Technology" or "General"
        - If about AI/ML/LLMs → "AI & Machine Learning"
        - If about coding tools/IDEs → "Development Tools"
        - If about crypto/blockchain → "Crypto & Web3"
        - If about productivity/automation tools → "Automation & Productivity"
        - NEVER use platform name (Twitter, Reddit) as category or subcategory

        Provide a JSON response with this EXACT structure:
        {{
          "category": "ONE category from the list above",
          "subcategory": "Specific subcategory (e.g., 'AI Agents', 'LLMs', 'Trading Bots')",
          "content_type": "Type (Tutorial, News, Discussion, Tool, Resource, etc.)",
          "topics": ["topic1", "topic2", "topic3"],
          "key_concepts": ["concept1", "concept2", "concept3"],
          "summary": "Clear 2-3 sentence summary of key information",
          "why_valuable": "Why someone would bookmark this content",
          "sentiment": "Positive/Negative/Neutral/Mixed",
          "complexity_level": "Beginner/Intermediate/Advanced/Expert",
          "time_to_consume": "estimated reading/watching time in minutes",
          "actionable_items": ["specific action1", "specific action2"],
          "learning_value": "What you can learn from this (1-2 sentences)",
          "practical_applications": ["how to apply this knowledge"],
          "related_skills": ["skill1", "skill2"],
          "follow_up_research": ["what to research next"],
          "quality_indicators": ["why this is high/low quality content"],
          "tags": ["searchable", "keywords"],
          "confidence_score": 0.85,

          "rewrite_angles": [
            {{
              "persona": "technical",
              "angle": "How a developer/engineer would approach this topic",
              "hook": "The most compelling technical hook (1 sentence)",
              "key_points": ["Technical detail 1", "Technical detail 2", "Technical detail 3"],
              "target_audience": "Who this angle is for",
              "estimated_engagement": "high/medium/low"
            }},
            {{
              "persona": "builder",
              "angle": "How to build/ship something with this knowledge",
              "hook": "Action-oriented hook focused on building (1 sentence)",
              "key_points": ["Practical step 1", "Practical step 2", "Practical step 3"],
              "target_audience": "Makers, founders, product builders",
              "estimated_engagement": "high/medium/low"
            }},
            {{
              "persona": "learner",
              "angle": "Educational explanation for someone learning this topic",
              "hook": "Learning-focused hook that makes it accessible (1 sentence)",
              "key_points": ["Learning point 1", "Learning point 2", "Learning point 3"],
              "target_audience": "Beginners and students",
              "estimated_engagement": "high/medium/low"
            }},
            {{
              "persona": "trendsetter",
              "angle": "What's new/trending/cutting-edge about this",
              "hook": "Trend-focused hook that highlights what's emerging (1 sentence)",
              "key_points": ["Trend insight 1", "Trend insight 2", "Trend insight 3"],
              "target_audience": "Early adopters and innovators",
              "estimated_engagement": "high/medium/low"
            }},
            {{
              "persona": "thought_leader",
              "angle": "Big picture analysis and future implications",
              "hook": "Thought-provoking hook about larger implications (1 sentence)",
              "key_points": ["Strategic insight 1", "Strategic insight 2", "Strategic insight 3"],
              "target_audience": "Leaders and strategists",
              "estimated_engagement": "high/medium/low"
            }}
          ],

          "discovery_signals": {{
            "author_authority": "high/medium/low - Assess credibility based on engagement, follower count, content quality",
            "trend_relevance": "emerging/mainstream/declining - Is this topic trending or fading",
            "viral_potential": 75,
            "discussion_quality": "high/medium/low - Quality of conversation around this content",
            "unique_perspective": "yes/no - Does this offer a unique take or is it repetitive"
          }},

          "content_freshness": {{
            "publication_age": "Calculate age from created_at timestamp (hours/days/weeks)",
            "still_relevant": "yes/no - Is this content still useful or is it outdated",
            "time_sensitivity": "urgent/timely/evergreen - Does this need to be acted on now or is it timeless"
          }}
        }}

        Focus on PRACTICAL VALUE and ACTIONABLE INSIGHTS. Be specific and helpful.
        The rewrite_angles are CRITICAL - provide detailed, distinct approaches for each persona.
        The discovery_signals help determine content worth and discoverability.
        The content_freshness helps with timing and relevance.

        Return ONLY valid JSON, no additional text.
        """
    
    def _analyze_with_mistral(self, prompt: str, sentiment_scores: Dict, service: Dict) -> Dict[str, Any]:
        """Analyze content using Mistral AI"""
        
        response = requests.post(
            f"{service['base_url']}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {service['key']}"
            },
            json={
                "model": service['model'],
                "messages": [
                    {"role": "system", "content": "You are an expert content analyst specializing in extracting maximum value from social media bookmarks. Provide detailed, actionable insights."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.1
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Clean JSON response
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            try:
                analysis = json.loads(content)
                # Ensure analysis is a dictionary
                if not isinstance(analysis, dict):
                    raise ValueError(f"Analysis result is not a dictionary: {type(analysis)}")
                    
                analysis['sentiment_scores'] = sentiment_scores
                analysis['ai_service'] = 'mistral'
                
                return analysis
            except (json.JSONDecodeError, ValueError) as e:
                raise Exception(f"Failed to parse Mistral response as JSON: {e}")
        else:
            raise Exception(f"Mistral API error: {response.status_code}")

    def _analyze_with_ollama(self, prompt: str, sentiment_scores: Dict, service: Dict) -> Dict[str, Any]:
        """Analyze content using Ollama"""
        try:
            url = f"{service['url']}/api/chat"
            payload = {
                "model": service['model'],
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert content analyst providing deep insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            # Add timeout to prevent hanging
            resp = requests.post(url, json=payload, timeout=30)  # 30 second timeout
            resp.raise_for_status()
            
            result = resp.json()
            content = result["message"]["content"]
            
            # Parse the JSON response
            try:
                parsed = json.loads(content)
                parsed['sentiment_scores'] = sentiment_scores
                parsed['ai_service'] = 'ollama'
                return parsed
            except json.JSONDecodeError:
                # If parsing fails, create a basic structure
                return {
                    'summary': content[:500],
                    'key_concepts': [],
                    'category': 'General',
                    'sentiment_scores': sentiment_scores,
                    'ai_service': 'ollama'
                }
                
        except requests.exceptions.Timeout:
            print("⚠️ Ollama request timed out")
            raise Exception("Ollama analysis timed out")
        except Exception as e:
            print(f"⚠️ Ollama analysis failed: {e}")
            raise
    
    def _analyze_with_gemini(self, prompt: str, sentiment_scores: Dict, service: Dict) -> Dict[str, Any]:
        """Analyze content using Google Gemini"""
        
        response = service['model'].generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1500
            )
        )
        
        content = response.text.strip()
        
        # Clean JSON response
        if content.startswith('```json'):
            content = content[7:-3]
        elif content.startswith('```'):
            content = content[3:-3]
        
        try:
            analysis = json.loads(content)
            # Ensure analysis is a dictionary
            if not isinstance(analysis, dict):
                raise ValueError(f"Analysis result is not a dictionary: {type(analysis)}")
                
            analysis['sentiment_scores'] = sentiment_scores
            analysis['ai_service'] = 'gemini'
            
            return analysis
        except (json.JSONDecodeError, ValueError) as e:
            raise Exception(f"Failed to parse Gemini response as JSON: {e}")
    
    def _analyze_comments(self, post: SocialPost) -> Dict[str, Any]:
        """Analyze Reddit comments to extract valuable insights"""
        
        # This would integrate with Reddit API to get comments
        # For now, return placeholder structure
        return {
            'top_insights': [
                "Most valuable comment insights would appear here",
                "Community consensus and expert opinions",
                "Practical tips and experiences shared"
            ],
            'expert_opinions': [],
            'common_questions': [],
            'practical_tips': [],
            'warnings_caveats': [],
            'additional_resources': []
        }
    
    def _analyze_media_content(self, media_urls: List[str]) -> Dict[str, Any]:
        """Analyze images and videos using AI vision"""
        
        media_insights = {
            'total_media': len(media_urls),
            'analyzed_media': 0,
            'insights': []
        }
        
        for url in media_urls[:3]:  # Analyze first 3 media items
            try:
                insight = self._analyze_single_media(url)
                if insight:
                    media_insights['insights'].append(insight)
                    media_insights['analyzed_media'] += 1
            except Exception as e:
                print(f"⚠️ Media analysis failed for {url}: {e}")
        
        return media_insights
    
    def _analyze_single_media(self, media_url: str) -> Optional[Dict[str, Any]]:
        """Analyze a single media item using AI vision"""

        # Check if we have Gemini Vision available
        for service in self.ai_services:
            if service['name'] == 'gemini' and 'vision_model' in service:
                try:
                    # Download image
                    response = requests.get(media_url, timeout=10)
                    if response.status_code != 200:
                        print(f"Failed to download image: {media_url}")
                        continue

                    # Save image temporarily
                    from PIL import Image
                    from io import BytesIO

                    img = Image.open(BytesIO(response.content))

                    # Create comprehensive vision analysis prompt
                    vision_prompt = """
                    Analyze this image from a social media post and provide structured insights.

                    Return a JSON response with this structure:
                    {
                      "content_type": "diagram/code/screenshot/infographic/photo/chart/other",
                      "description": "What is shown in the image (2-3 sentences)",
                      "key_elements": ["element1", "element2", "element3"],
                      "extracted_text": "Any visible text or code (if applicable)",
                      "technical_concepts": ["concept1", "concept2"],
                      "educational_value": "high/medium/low",
                      "practical_insights": ["insight1", "insight2"],
                      "adds_value": "yes/no - Does this image add significant value to understanding the content?"
                    }

                    Focus on technical, educational, and practical value.
                    Return ONLY valid JSON, no additional text.
                    """

                    # Use Gemini Vision to analyze
                    vision_response = service['vision_model'].generate_content(
                        [vision_prompt, img],
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.1,
                            max_output_tokens=800
                        )
                    )

                    # Parse the response
                    content = vision_response.text.strip()

                    # Clean JSON response
                    if content.startswith('```json'):
                        content = content[7:-3]
                    elif content.startswith('```'):
                        content = content[3:-3]

                    import json
                    vision_analysis = json.loads(content)

                    # Add metadata
                    vision_analysis['media_url'] = media_url
                    vision_analysis['analyzed_with'] = 'gemini-vision'

                    print(f"✅ Vision analysis complete: {vision_analysis.get('content_type', 'unknown')}")

                    return vision_analysis

                except Exception as e:
                    print(f"⚠️ Vision analysis failed for {media_url}: {e}")
                    # Return basic analysis as fallback
                    return {
                        'media_url': media_url,
                        'content_type': 'image',
                        'description': 'Vision analysis unavailable',
                        'key_elements': [],
                        'educational_value': 'unknown',
                        'extracted_text': '',
                        'analyzed_with': 'basic'
                    }

        # No vision service available
        return {
            'media_url': media_url,
            'content_type': 'image',
            'description': 'No vision AI service available',
            'key_elements': [],
            'educational_value': 'unknown',
            'extracted_text': '',
            'analyzed_with': 'none'
        }
    
    def _calculate_intelligent_value_score(self, analysis: Dict, post: SocialPost) -> float:
        """Calculate sophisticated value score based on multiple factors"""
        
        score = 5.0  # Base score
        
        # Content quality indicators
        if 'quality_indicators' in analysis:
            quality_count = len(analysis['quality_indicators'])
            score += min(quality_count * 0.5, 2.0)
        
        # Actionable content bonus
        if 'actionable_items' in analysis:
            actionable_count = len(analysis['actionable_items'])
            score += min(actionable_count * 0.3, 1.5)
        
        # Learning value bonus
        if 'learning_value' in analysis and analysis['learning_value']:
            score += 1.0
        
        # Engagement quality (not just quantity)
        if post.engagement:
            # High engagement with good content is valuable
            likes = post.engagement.get('likes', 0)
            comments = post.engagement.get('comments', 0)
            if likes > 100 or comments > 20:
                score += 0.5
        
        # Platform-specific adjustments
        if post.platform == 'reddit':
            # Reddit discussions often have high value
            score += 0.5
        elif post.platform == 'twitter':
            # Twitter threads can be valuable
            if post.post_type == 'thread':
                score += 0.5
        
        # Content complexity and depth
        if 'complexity_level' in analysis:
            complexity = analysis['complexity_level']
            if complexity in ['Advanced', 'Expert']:
                score += 0.5
        
        # Cap the score at 10
        return min(score, 10.0)
    
    def _calculate_content_quality_score(self, analysis: Dict, post: SocialPost) -> float:
        """
        Calculate content quality score for social media reposting (0-10 scale)
        
        Optimized for content that works well on social media:
        - Clarity and readability
        - Engagement potential
        - Information value
        - Shareability factors
        """
        
        quality_score = 0.0
        content = post.content.lower()
        original_content = post.content
        
        # Base content value (0-3 points)
        content_length = len(original_content)
        if 50 <= content_length <= 280:  # Twitter-optimal length
            quality_score += 3.0
        elif 280 < content_length <= 500:  # Good for LinkedIn/Facebook
            quality_score += 2.5
        elif content_length > 500:  # Long-form content
            quality_score += 2.0
        elif content_length < 50:  # Too short
            quality_score += 0.5
        
        # Engagement indicators (0-2 points)
        engagement_words = ['tip', 'hack', 'secret', 'amazing', 'incredible', 'must-know', 
                           'game-changer', 'breakthrough', 'revolutionary', 'insider']
        engagement_count = sum(1 for word in engagement_words if word in content)
        quality_score += min(engagement_count * 0.5, 2.0)
        
        # Technical value (0-2 points)
        tech_value_terms = ['ai', 'ml', 'python', 'javascript', 'react', 'api', 'database',
                           'algorithm', 'framework', 'tool', 'software', 'code', 'dev']
        tech_count = sum(1 for term in tech_value_terms if term in content)
        quality_score += min(tech_count * 0.3, 2.0)
        
        # Structure and readability (0-1.5 points)
        if any(indicator in content for indicator in ['1.', '2.', '3.', '•', '-', 'first', 'second']):
            quality_score += 1.0
        if '\n' in original_content:  # Has line breaks
            quality_score += 0.5
        
        # Social media friendly elements (0-1.5 points)
        if any(indicator in content for indicator in ['#', '@', 'http', 'link']):
            quality_score += 0.5
        if any(indicator in content for indicator in ['?', '!', 'what', 'how', 'why']):
            quality_score += 0.5  # Questions/exclamations engage better
        if any(emoji_indicator in original_content for emoji_indicator in ['🚀', '💡', '🔥', '✨', '⚡']):
            quality_score += 0.5
        
        # Actual engagement metrics (0-1 point)
        if hasattr(post, 'engagement') and post.engagement:
            likes = post.engagement.get('likes', 0) or post.engagement.get('score', 0) or post.engagement.get('favorite_count', 0)
            comments = post.engagement.get('replies', 0) or post.engagement.get('num_comments', 0) or post.engagement.get('reply_count', 0)
            
            if likes > 100 or comments > 20:
                quality_score += 1.0
            elif likes > 20 or comments > 5:
                quality_score += 0.5
        
        return min(quality_score, 10.0)
    
    def _determine_rewrite_candidate(self, analysis: Dict, post: SocialPost, quality_score: float) -> bool:
        """
        Determine if content is a good candidate for rewriting and reposting to social media
        
        A post is a rewrite candidate if:
        - It has good information but poor social media presentation
        - It's too long for optimal social media engagement
        - It lacks engaging elements but has valuable content
        - It has potential but needs optimization for social platforms
        """
        
        content = post.content
        content_lower = content.lower()
        content_length = len(content)
        
        # High-quality content that's too long for social media
        if quality_score >= 6.0 and content_length > 500:
            return True
        
        # Good technical content but lacks social media engagement elements
        tech_terms = ['ai', 'ml', 'python', 'javascript', 'react', 'api', 'database',
                     'algorithm', 'framework', 'tool', 'software', 'code', 'dev']
        has_tech_content = sum(1 for term in tech_terms if term in content_lower) >= 2
        
        engagement_elements = ['#', '@', '?', '!', '🚀', '💡', '🔥', '✨', '⚡']
        has_engagement_elements = any(element in content for element in engagement_elements)
        
        if has_tech_content and not has_engagement_elements and quality_score >= 4.0:
            return True
        
        # Content with good structure but could be more engaging
        has_structure = any(indicator in content_lower for indicator in ['1.', '2.', '3.', '•', '-', 'first', 'second'])
        engagement_words = ['tip', 'hack', 'secret', 'amazing', 'incredible', 'must-know', 
                           'game-changer', 'breakthrough', 'revolutionary', 'insider']
        has_engagement_words = any(word in content_lower for word in engagement_words)
        
        if has_structure and not has_engagement_words and quality_score >= 5.0:
            return True
        
        # Long posts with good content but poor social media optimization
        if content_length > 800 and quality_score >= 5.0:
            return True
        
        # Posts with valuable information but suboptimal length for social media
        if content_length < 50 and quality_score >= 6.0:  # Too short but high quality
            return True
        
        # Posts with good engagement potential but missing key elements
        if quality_score >= 7.0 and not has_engagement_elements:
            return True
        
        # Check for posts that performed well but could be optimized further
        if hasattr(post, 'engagement') and post.engagement:
            likes = post.engagement.get('likes', 0) or post.engagement.get('score', 0) or post.engagement.get('favorite_count', 0)
            comments = post.engagement.get('replies', 0) or post.engagement.get('num_comments', 0) or post.engagement.get('reply_count', 0)
            
            # Good engagement but could be better with optimization
            if (likes > 50 or comments > 10) and quality_score >= 6.0 and not has_engagement_elements:
                return True
        
        return False
    
    def _generate_actionable_insights(self, analysis: Dict, post: SocialPost) -> List[str]:
        """Generate specific actionable insights from the analysis"""
        
        insights = []
        
        # Extract from analysis
        if 'actionable_items' in analysis:
            insights.extend(analysis['actionable_items'])
        
        # Add platform-specific insights
        if post.platform == 'reddit':
            insights.append(f"Explore discussion thread for community insights: {post.url}")
        
        if 'follow_up_research' in analysis:
            for research in analysis['follow_up_research']:
                insights.append(f"Research: {research}")
        
        return insights[:5]  # Return top 5 insights
    
    def _generate_learning_recommendations(self, analysis: Dict, post: SocialPost) -> Dict[str, Any]:
        """Generate personalized learning recommendations"""
        
        return {
            'next_steps': analysis.get('follow_up_research', []),
            'related_skills': analysis.get('related_skills', []),
            'difficulty_level': analysis.get('complexity_level', 'Unknown'),
            'estimated_time': analysis.get('time_to_consume', 'Unknown'),
            'prerequisites': [],
            'learning_path': []
        }
    
    def _basic_analysis(self, post: SocialPost, sentiment_scores: Dict) -> Dict[str, Any]:
        """Fallback basic analysis when AI services are unavailable"""

        # Basic rewrite angles when AI is not available
        basic_rewrite_angles = [
            {
                "persona": "technical",
                "angle": "Technical breakdown of this content",
                "hook": "Here's what you need to know from a technical perspective",
                "key_points": ["Main technical concept", "Implementation details", "Best practices"],
                "target_audience": "Developers and engineers",
                "estimated_engagement": "medium"
            },
            {
                "persona": "builder",
                "angle": "How to apply this in your projects",
                "hook": "Build something with this knowledge",
                "key_points": ["Practical application", "Quick implementation", "Real-world use case"],
                "target_audience": "Makers and builders",
                "estimated_engagement": "medium"
            },
            {
                "persona": "learner",
                "angle": "Understanding the fundamentals",
                "hook": "Learn the basics step by step",
                "key_points": ["Core concept explained", "Why it matters", "How to get started"],
                "target_audience": "Beginners",
                "estimated_engagement": "medium"
            },
            {
                "persona": "trendsetter",
                "angle": "Why this is relevant now",
                "hook": "This is trending and here's why",
                "key_points": ["Current trend", "Market momentum", "Early adoption opportunity"],
                "target_audience": "Innovators",
                "estimated_engagement": "medium"
            },
            {
                "persona": "thought_leader",
                "angle": "Strategic implications",
                "hook": "What this means for the future",
                "key_points": ["Industry impact", "Future trends", "Strategic considerations"],
                "target_audience": "Leaders and strategists",
                "estimated_engagement": "medium"
            }
        ]

        # Calculate content age
        from datetime import datetime
        try:
            created_dt = datetime.fromisoformat(post.created_at.replace('Z', '+00:00'))
            age_hours = (datetime.now(created_dt.tzinfo) - created_dt).total_seconds() / 3600
            if age_hours < 24:
                publication_age = f"{int(age_hours)} hours"
            elif age_hours < 168:  # 7 days
                publication_age = f"{int(age_hours/24)} days"
            else:
                publication_age = f"{int(age_hours/168)} weeks"
        except Exception:
            publication_age = "unknown"

        return {
            'category': 'General',
            'subcategory': post.platform.title(),
            'content_type': post.post_type,
            'topics': post.hashtags[:3] if post.hashtags else ['general'],
            'key_concepts': [],
            'summary': post.content[:200] + '...' if len(post.content) > 200 else post.content,
            'why_valuable': 'User bookmarked this content',
            'sentiment': 'Neutral',
            'complexity_level': 'Unknown',
            'time_to_consume': 'Unknown',
            'actionable_items': [],
            'learning_value': 'Content analysis not available',
            'practical_applications': [],
            'related_skills': [],
            'follow_up_research': [],
            'quality_indicators': [],
            'tags': post.hashtags[:5] if post.hashtags else [],
            'confidence_score': 0.3,
            'sentiment_scores': sentiment_scores,
            'ai_service': 'basic',
            'rewrite_angles': basic_rewrite_angles,
            'discovery_signals': {
                'author_authority': 'medium',
                'trend_relevance': 'unknown',
                'viral_potential': 50,
                'discussion_quality': 'unknown',
                'unique_perspective': 'unknown'
            },
            'content_freshness': {
                'publication_age': publication_age,
                'still_relevant': 'yes',
                'time_sensitivity': 'evergreen'
            }
        }


# Example usage and testing
if __name__ == "__main__":
    analyzer = IntelligentContentAnalyzer()
    print("🧠 Intelligent Content Analyzer ready!")