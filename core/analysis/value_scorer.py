"""
Sophisticated Value Scoring System for PrisMind
Analyzes content quality, relevance, and learning potential to assign intelligent value scores
"""

import re
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import math

class ValueScorer:
    """Sophisticated value scoring system for social media content"""
    
    def __init__(self):
        # Load quality indicators and patterns
        self.quality_indicators = self._load_quality_patterns()
        self.learning_keywords = self._load_learning_keywords()
        self.spam_indicators = self._load_spam_patterns()
    
    def calculate_value_score(self, post_data: Dict[str, Any]) -> float:
        """Calculate comprehensive value score for a post"""
        
        # Base score
        score = 5.0
        
        # Content quality analysis (40% of score)
        content_score = self._analyze_content_quality(post_data)
        score += content_score * 0.4
        
        # Engagement quality analysis (25% of score)
        engagement_score = self._analyze_engagement_quality(post_data)
        score += engagement_score * 0.25
        
        # Learning potential analysis (20% of score)
        learning_score = self._analyze_learning_potential(post_data)
        score += learning_score * 0.2
        
        # Recency and relevance (10% of score)
        recency_score = self._analyze_recency_relevance(post_data)
        score += recency_score * 0.1
        
        # Platform-specific adjustments (5% of score)
        platform_score = self._analyze_platform_factors(post_data)
        score += platform_score * 0.05
        
        # Apply penalties for spam/low-quality content
        penalty = self._calculate_penalties(post_data)
        score -= penalty
        
        # Clamp score between 1-10
        return max(1.0, min(10.0, round(score, 1)))
    
    def _analyze_content_quality(self, post_data: Dict[str, Any]) -> float:
        """Analyze content quality factors"""
        content = post_data.get('content', '') or ''
        if not content or content.lower() == 'none':
            return -2.0
        
        quality_score = 0.0
        
        # Length analysis
        length = len(content.strip())
        if length < 20:
            quality_score -= 2.0  # Too short
        elif length < 50:
            quality_score -= 1.0  # Very short
        elif 100 <= length <= 500:
            quality_score += 1.0  # Good length
        elif 500 < length <= 1000:
            quality_score += 1.5  # Detailed
        elif length > 2000:
            quality_score -= 0.5  # Potentially too long
        
        # Quality indicators
        content_lower = content.lower()
        
        # Positive quality indicators
        positive_patterns = [
            (r'\bhow to\b', 1.5, 'tutorial'),
            (r'\bexplain\w*\b', 1.0, 'explanation'),
            (r'\blearn\w*\b', 1.0, 'educational'),
            (r'\btutorial\b', 1.5, 'tutorial'),
            (r'\bguide\b', 1.0, 'guide'),
            (r'\btip\w*\b', 0.8, 'tips'),
            (r'\binsight\w*\b', 1.0, 'insights'),
            (r'\banalysis\b', 1.2, 'analysis'),
            (r'\bresearch\b', 1.5, 'research'),
            (r'\bstudy\b', 1.2, 'study'),
            (r'\bdata\b', 1.0, 'data'),
            (r'\bevidence\b', 1.2, 'evidence'),
            (r'\bexample\w*\b', 0.8, 'examples'),
            (r'\bcase study\b', 1.5, 'case_study'),
            (r'\bbest practice\w*\b', 1.3, 'best_practices'),
            (r'\blessons? learned\b', 1.2, 'lessons'),
            (r'\bmistake\w*\b', 0.8, 'mistakes'),
            (r'\bsolution\w*\b', 1.0, 'solutions'),
            (r'\bframework\b', 1.2, 'framework'),
            (r'\bmethodology\b', 1.3, 'methodology')
        ]
        
        for pattern, score_boost, category in positive_patterns:
            if re.search(pattern, content_lower):
                quality_score += score_boost
        
        # Structure quality
        if self._has_good_structure(content):
            quality_score += 1.0
        
        # Technical depth indicators
        if self._has_technical_depth(content):
            quality_score += 1.5
        
        # Actionable content
        if self._is_actionable(content):
            quality_score += 1.0
        
        return quality_score
    
    def _analyze_engagement_quality(self, post_data: Dict[str, Any]) -> float:
        """Analyze engagement quality vs quantity"""
        platform = post_data.get('platform', '').lower()
        engagement_score = 0.0
        
        if platform == 'reddit':
            score = post_data.get('engagement_score', 0)
            upvote_ratio = post_data.get('upvote_ratio', 0.5)
            num_comments = post_data.get('num_comments', 0)
            
            # Score-based quality (Reddit upvotes are meaningful)
            if score > 1000:
                engagement_score += 2.0
            elif score > 500:
                engagement_score += 1.5
            elif score > 100:
                engagement_score += 1.0
            elif score > 50:
                engagement_score += 0.5
            elif score < 5:
                engagement_score -= 1.0
            
            # Upvote ratio quality
            if upvote_ratio > 0.9:
                engagement_score += 1.5
            elif upvote_ratio > 0.8:
                engagement_score += 1.0
            elif upvote_ratio < 0.6:
                engagement_score -= 1.0
            
            # Comments indicate discussion
            if num_comments > 100:
                engagement_score += 1.0
            elif num_comments > 50:
                engagement_score += 0.5
            
        elif platform == 'twitter':
            # Accept either flat metrics or nested engagement dict
            engagement = post_data.get('engagement') or {}
            likes = post_data.get('likes', engagement.get('likes', 0))
            retweets = post_data.get('retweets', engagement.get('retweets', 0))
            replies = post_data.get('replies', engagement.get('comments', engagement.get('replies', 0)))
            
            # Twitter engagement is more inflated, so higher thresholds
            total_engagement = likes + (retweets * 2) + (replies * 3)
            
            if total_engagement > 10000:
                engagement_score += 2.0
            elif total_engagement > 5000:
                engagement_score += 1.5
            elif total_engagement > 1000:
                engagement_score += 1.0
            elif total_engagement > 100:
                engagement_score += 0.5
            elif total_engagement < 10:
                engagement_score -= 0.5
            
            # Retweet to like ratio (retweets are more meaningful)
            if likes > 0:
                rt_ratio = retweets / likes
                if rt_ratio > 0.1:  # High retweet ratio indicates shareworthy content
                    engagement_score += 1.0
        
        # Ensure engagement score stays within 0..10 range bounds used by tests
        return max(0.0, min(10.0, engagement_score))
    
    def _analyze_learning_potential(self, post_data: Dict[str, Any]) -> float:
        """Analyze educational and learning value"""
        content = post_data.get('content', '').lower()
        learning_score = 0.0
        
        # Learning keywords
        learning_patterns = [
            (r'\blearn\w*\b', 1.0),
            (r'\bteach\w*\b', 1.0),
            (r'\beducation\w*\b', 0.8),
            (r'\bskill\w*\b', 0.8),
            (r'\bknowledge\b', 0.8),
            (r'\bunderstand\w*\b', 0.6),
            (r'\bexplain\w*\b', 0.8),
            (r'\bconcept\w*\b', 0.8),
            (r'\btheory\b', 0.8),
            (r'\bpractice\b', 0.6),
            (r'\bappl\w*\b', 0.6),  # application, apply, etc.
            (r'\bimplement\w*\b', 0.8),
            (r'\bstrateg\w*\b', 0.8),
            (r'\btechnique\w*\b', 0.8),
            (r'\bmethod\w*\b', 0.6),
            (r'\bapproach\b', 0.6),
            (r'\bprocess\b', 0.6),
            (r'\bworkflow\b', 0.8),
            (r'\bbest practice\w*\b', 1.2),
            (r'\blessons? learned\b', 1.0)
        ]
        
        for pattern, score in learning_patterns:
            if re.search(pattern, content):
                learning_score += score
        
        # Category-specific learning value
        category = post_data.get('category', '').lower()
        high_learning_categories = [
            'tutorial', 'education', 'programming', 'technology',
            'science', 'research', 'analysis', 'guide', 'how-to'
        ]
        
        if any(cat in category for cat in high_learning_categories):
            learning_score += 1.0
        
        # Check for step-by-step content
        if self._has_step_by_step_content(content):
            learning_score += 1.5
        
        # Check for code examples or technical details
        if self._has_technical_examples(content):
            learning_score += 1.0
        
        return min(learning_score, 3.0)  # Cap at 3.0
    
    def _analyze_recency_relevance(self, post_data: Dict[str, Any]) -> float:
        """Analyze recency and ongoing relevance"""
        recency_score = 0.0
        
        # Parse creation date
        created_at = post_data.get('created_at')
        if created_at:
            try:
                if isinstance(created_at, str):
                    post_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    post_date = created_at
                
                now = datetime.now(post_date.tzinfo) if post_date.tzinfo else datetime.now()
                age_days = (now - post_date).days
                
                # Recency scoring
                if age_days < 1:
                    recency_score += 1.0  # Very recent
                elif age_days < 7:
                    recency_score += 0.8  # Recent
                elif age_days < 30:
                    recency_score += 0.5  # Somewhat recent
                elif age_days < 90:
                    recency_score += 0.2  # Still relevant
                elif age_days > 365:
                    recency_score -= 0.5  # Potentially outdated
                
            except Exception:
                pass  # Ignore date parsing errors
        
        # Evergreen content indicators
        content = post_data.get('content', '').lower()
        evergreen_patterns = [
            'fundamental', 'principle', 'basic', 'concept', 'theory',
            'always', 'timeless', 'classic', 'essential', 'core'
        ]
        
        if any(pattern in content for pattern in evergreen_patterns):
            recency_score += 0.5  # Evergreen content bonus
        
        return recency_score
    
    def _analyze_platform_factors(self, post_data: Dict[str, Any]) -> float:
        """Platform-specific quality factors"""
        platform = post_data.get('platform', '').lower()
        platform_score = 0.0
        
        if platform == 'reddit':
            # Reddit tends to have more in-depth discussions
            subreddit = post_data.get('folder_category', '').lower()
            
            # High-quality subreddits
            quality_subreddits = [
                'askscience', 'explainlikeimfive', 'todayilearned',
                'programming', 'learnprogramming', 'datascience',
                'machinelearning', 'askhistorians', 'changemyview'
            ]
            
            if any(sub in subreddit for sub in quality_subreddits):
                platform_score += 1.0
        
        elif platform == 'twitter':
            # Twitter threads tend to be higher quality
            content = post_data.get('content', '')
            if 'thread' in content.lower() or '1/' in content:
                platform_score += 0.5
        
        return platform_score
    
    def _calculate_penalties(self, post_data: Dict[str, Any]) -> float:
        """Calculate penalties for low-quality content"""
        penalty = 0.0
        content = post_data.get('content', '').lower()
        
        # Spam indicators
        spam_patterns = [
            (r'\b(buy|sell|discount|offer|deal)\b.*\b(now|today|limited)\b', 2.0),
            (r'\bclick here\b', 1.0),
            (r'\bfree money\b', 2.0),
            (r'\bget rich\b', 2.0),
            (r'\bmake money fast\b', 2.0),
            (r'!!!+', 1.0),  # Multiple exclamation marks
            (r'\b(urgent|hurry|act now)\b', 1.0)
        ]
        
        for pattern, penalty_score in spam_patterns:
            if re.search(pattern, content):
                penalty += penalty_score
        
        # Low-quality indicators
        if len(content.strip()) < 10:
            penalty += 2.0
        
        # Too many caps
        if content.isupper() and len(content) > 20:
            penalty += 1.0
        
        # Excessive emoji usage
        emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', content))
        if emoji_count > 5:
            penalty += 0.5
        
        return penalty
    
    def _has_good_structure(self, content: str) -> bool:
        """Check if content has good structure"""
        # Look for lists, numbered points, headers
        structure_indicators = [
            r'^\d+\.',  # Numbered lists
            r'^[-*•]',  # Bullet points
            r'^#{1,6}\s',  # Headers
            r':\s*$',  # Colons (indicating lists)
        ]
        
        lines = content.split('\n')
        structured_lines = 0
        
        for line in lines:
            line = line.strip()
            if any(re.search(pattern, line, re.MULTILINE) for pattern in structure_indicators):
                structured_lines += 1
        
        return structured_lines >= 2
    
    def _has_technical_depth(self, content: str) -> bool:
        """Check for technical depth indicators"""
        technical_patterns = [
            r'\bcode\b', r'\bfunction\b', r'\balgorithm\b', r'\bAPI\b',
            r'\bdatabase\b', r'\bframework\b', r'\blibrary\b', r'\bsoftware\b',
            r'\barchitecture\b', r'\bdesign pattern\b', r'\boptimization\b',
            r'\bperformance\b', r'\bscalability\b', r'\bsecurity\b'
        ]
        
        content_lower = content.lower()
        return sum(1 for pattern in technical_patterns if re.search(pattern, content_lower)) >= 2
    
    def _is_actionable(self, content: str) -> bool:
        """Check if content provides actionable information"""
        actionable_patterns = [
            r'\bstep\w*\b', r'\bdo\b', r'\btry\b', r'\buse\b', r'\bapply\b',
            r'\bimplement\b', r'\bstart\b', r'\bbegin\b', r'\bfollow\b',
            r'\bpractice\b', r'\bexercise\b', r'\baction\w*\b'
        ]
        
        content_lower = content.lower()
        return sum(1 for pattern in actionable_patterns if re.search(pattern, content_lower)) >= 2
    
    def _has_step_by_step_content(self, content: str) -> bool:
        """Check for step-by-step instructions"""
        step_patterns = [
            r'step \d+', r'\d+\.\s', r'first.*second.*third',
            r'next.*then.*finally', r'begin.*then.*end'
        ]
        
        content_lower = content.lower()
        return any(re.search(pattern, content_lower) for pattern in step_patterns)
    
    def _has_technical_examples(self, content: str) -> bool:
        """Check for code examples or technical details"""
        return bool(re.search(r'```|`[^`]+`|\bcode\b.*example|\bsyntax\b', content, re.IGNORECASE))
    
    def _load_quality_patterns(self) -> Dict:
        """Load quality pattern configurations"""
        return {
            'high_quality': [
                'tutorial', 'guide', 'explanation', 'analysis', 'research',
                'study', 'framework', 'methodology', 'best practices'
            ],
            'medium_quality': [
                'tips', 'advice', 'opinion', 'discussion', 'question'
            ],
            'low_quality': [
                'rant', 'complaint', 'spam', 'advertisement'
            ]
        }
    
    def _load_learning_keywords(self) -> List[str]:
        """Load learning-related keywords"""
        return [
            'learn', 'teach', 'education', 'tutorial', 'guide',
            'how-to', 'explain', 'understand', 'concept', 'skill'
        ]
    
    def _load_spam_patterns(self) -> List[str]:
        """Load spam detection patterns"""
        return [
            r'\b(buy|sell|discount|offer|deal)\b.*\b(now|today|limited)\b',
            r'\bclick here\b',
            r'\bfree money\b',
            r'\bget rich\b',
            r'!!!+'
        ]