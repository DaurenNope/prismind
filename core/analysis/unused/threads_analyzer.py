import os
import requests
import re
from loguru import logger
from typing import Dict, Any, List
from core.extraction.social_extractor_base import SocialPost

class ThreadsAnalyzer:
    """AI content analyzer for Threads posts using Mistral AI"""

    def __init__(self):
        self.api_key = os.getenv('MISTRAL_API_KEY')
        self.base_url = "https://api.mistral.ai/v1"
        self.model = "mistral-small-latest"
        
        if not self.api_key:
            logger.warning("MISTRAL_API_KEY not found. ThreadsAnalyzer will perform basic analysis.")

    def analyze_thread(self, post: SocialPost) -> Dict[str, Any]:
        """Analyze a single Threads post (which could be a multi-message thread)."""
        if not self.api_key:
            return self._basic_analysis(post)

        try:
            logger.info(f"Analyzing Threads post {post.post_id} with Mistral AI...")
            
            prompt = self._create_thread_analysis_prompt(post)
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "You are an expert social media analyst specializing in summarizing conversation threads."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1200,
                    "temperature": 0.2
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                logger.success(f"Mistral AI analysis for thread {post.post_id} complete.")
                return self._parse_ai_response(content)
            else:
                logger.error(f"Mistral API error for thread {post.post_id}: {response.status_code} - {response.text}")
                return self._basic_analysis(post)
                
        except Exception as e:
            logger.error(f"Mistral analysis failed for thread {post.post_id}: {e}")
            return self._basic_analysis(post)

    def _create_thread_analysis_prompt(self, post: SocialPost) -> str:
        """Create a detailed analysis prompt for a multi-message thread."""
        return f"""
Analyze the following conversation thread from Threads. The content contains multiple messages separated by '---'.

**Thread Content:**
---
{post.content}
---
**Original Post URL:** {post.url}
**Author:** {post.author_handle}

**Instructions:**
Based on the full conversation, please provide the following:
1.  **Primary Topic:** A few keywords describing the main subject (e.g., "AI in marketing," "Python programming tip," "New design tool").
2.  **Category:** Choose the most fitting category from this list: Technology, Business, AI, Marketing, Finance, Art, Health & Wellness, Lifestyle, Entertainment, Personal Development, Real Estate, Other.
3.  **Key Takeaways:** A bulleted list of the most important points, conclusions, or pieces of advice from the entire thread.
4.  **Overall Summary:** A concise, 2-3 sentence summary of the conversation's purpose and outcome.
5.  **Sentiment:** The overall sentiment of the thread (Positive, Negative, Neutral, Mixed).
6.  **Value Score (1-10):** Based on the thread's usefulness, insightfulness, and reference value. (1=low, 10=high).

**Format your response exactly as follows:**
TOPIC: [Your response]
CATEGORY: [Your response]
TAKEAWAYS:
- [Takeaway 1]
- [Takeaway 2]
- [Takeaway 3]
SUMMARY: [Your response]
SENTIMENT: [Your response]
VALUE_SCORE: [Your score]
"""

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse the structured AI response into a dictionary using regex for robustness."""
        
        def get_value(key: str, default: Any = '') -> Any:
            """Safely extracts a value using regex."""
            match = re.search(f"^{key}:\\s*(.*)$", response, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1).strip()
            return default

        try:
            category = get_value('CATEGORY', 'Uncategorized')
            
            # Find all takeaway bullet points
            takeaways = re.findall(r"^\s*-\s*(.*)$", response, re.MULTILINE)
            
            score_str = get_value('VALUE_SCORE', '5')
            value_score = int(''.join(filter(str.isdigit, score_str))) if score_str else 5

            return {
                'topic': get_value('TOPIC', 'Uncategorized'),
                'category': category if category else 'Uncategorized',
                'takeaways': takeaways,
                'summary': get_value('SUMMARY', ''),
                'sentiment': get_value('SENTIMENT', 'Neutral'),
                'value_score': value_score
            }
        except Exception as e:
            logger.error(f"Error parsing AI response for Thread with regex: {e}")
            # Return a default structure on error
            return {
                'topic': 'Uncategorized', 'category': 'Uncategorized', 'takeaways': [],
                'summary': 'Failed to parse AI response.', 'sentiment': 'Neutral', 'value_score': 1
            }

    def _basic_analysis(self, post: SocialPost) -> Dict[str, Any]:
        """Provide a basic, non-AI analysis as a fallback."""
        return {
            'topic': 'Threads Post',
            'category': 'Uncategorized',
            'takeaways': [],
            'summary': f"A thread by {post.author_handle}. Content starts with: \"{post.content[:150]}...\"",
            'sentiment': 'Neutral',
            'value_score': 3
        }
        
    def analyze_batch(self, posts: List[SocialPost]) -> List[Dict]:
        """Analyzes a batch of Threads posts and returns them in a standard format."""
        analyzed_posts = []
        for i, post in enumerate(posts):
            if post.platform != 'threads':
                continue

            logger.info(f"Analyzing Threads post {i+1}/{len(posts)}...")
            analysis_results = self.analyze_thread(post)

            analyzed_posts.append({
                'post': post,
                'analysis': {
                    'category': analysis_results.get('category', 'Uncategorized'),
                    'subcategory': analysis_results.get('topic', ''),
                    'content_type': 'Thread',
                    'summary': analysis_results.get('summary', ''),
                    'sentiment': analysis_results.get('sentiment', 'Neutral'),
                    'value_score': analysis_results.get('value_score', 5),
                    'tags': analysis_results.get('takeaways', [])[:5], # Use takeaways as tags
                    'confidence_score': 0.9 if self.api_key else 0.1
                }
            })
        return analyzed_posts 