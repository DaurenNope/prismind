"""
Intelligent Comment Analysis for PrisMind
Analyzes Reddit comments to extract valuable insights and discussions
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

class CommentAnalyzer:
    """Analyzes Reddit comments to extract valuable insights"""
    
    def __init__(self):
        self.cache_file = Path("output/data/comment_analysis_cache.json")
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.analysis_cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load cached comment analyses"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading comment cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save comment analyses to cache"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error saving comment cache: {e}")
    
    def analyze_comments(self, comments: List[Dict], post_context: str = "") -> Dict[str, Any]:
        """Analyze a list of comments and extract valuable insights"""
        if not comments:
            return {"insights": [], "summary": "No comments available", "value_score": 0}
        
        # Create cache key
        cache_key = self._generate_cache_key(comments, post_context)
        
        # Check cache first
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]
        
        analysis = self._perform_analysis(comments, post_context)
        
        # Cache the result
        self.analysis_cache[cache_key] = analysis
        self._save_cache()
        
        return analysis
    
    def _generate_cache_key(self, comments: List[Dict], post_context: str) -> str:
        """Generate a unique cache key for comment analysis"""
        comment_ids = [str(hash(c.get('content', '')[:100])) for c in comments[:3]]
        context_hash = str(hash(post_context[:100]))
        return f"comments_{'_'.join(comment_ids)}_{context_hash}"
    
    def _perform_analysis(self, comments: List[Dict], post_context: str) -> Dict[str, Any]:
        """Perform actual comment analysis"""
        insights = []
        total_score = 0
        valuable_comments = 0
        
        for comment in comments:
            comment_analysis = self._analyze_single_comment(comment, post_context)
            if comment_analysis['value_score'] > 5:
                insights.append(comment_analysis)
                valuable_comments += 1
            total_score += comment_analysis['value_score']
        
        # Generate summary
        summary = self._generate_comment_summary(comments, insights)
        
        # Calculate overall value score
        avg_score = total_score / len(comments) if comments else 0
        value_bonus = min(valuable_comments * 0.5, 3.0)  # Bonus for having valuable comments
        final_score = min(avg_score + value_bonus, 10.0)
        
        return {
            "insights": insights[:5],  # Top 5 insights
            "summary": summary,
            "value_score": round(final_score, 1),
            "total_comments": len(comments),
            "valuable_comments": valuable_comments,
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _analyze_single_comment(self, comment: Dict, post_context: str) -> Dict[str, Any]:
        """Analyze a single comment for value and insights"""
        content = comment.get('content', '')
        author = comment.get('author', 'Unknown')
        is_op = comment.get('is_op', False)
        platform = comment.get('platform', 'reddit')
        
        # Platform-specific scoring
        if platform == 'twitter':
            score = comment.get('likes', 0) + comment.get('retweets', 0) * 2
            # Twitter replies have different engagement patterns
            engagement_threshold_high = 100
            engagement_threshold_medium = 20
            engagement_threshold_low = 5
        elif platform == 'threads':
            score = comment.get('likes', 0) + comment.get('reposts', 0) * 2
            engagement_threshold_high = 50
            engagement_threshold_medium = 10
            engagement_threshold_low = 3
        else:  # Reddit
            score = comment.get('score', 0)
            engagement_threshold_high = 50
            engagement_threshold_medium = 20
            engagement_threshold_low = 5
        
        # Basic value scoring
        value_score = 3.0  # Base score
        
        # Length bonus (meaningful content)
        if len(content) > 200:
            value_score += 1.0
        elif len(content) > 100:
            value_score += 0.5
        
        # Platform-adjusted engagement bonus
        if score > engagement_threshold_high:
            value_score += 2.0
        elif score > engagement_threshold_medium:
            value_score += 1.0
        elif score > engagement_threshold_low:
            value_score += 0.5
        
        # OP response bonus
        if is_op:
            value_score += 1.0
        
        # Content quality indicators
        quality_indicators = [
            'explained', 'because', 'reason', 'example', 'experience',
            'actually', 'however', 'alternative', 'solution', 'recommend',
            'learned', 'discovered', 'found out', 'turns out', 'important',
            'correction', 'update', 'context', 'source', 'link'
        ]
        
        content_lower = content.lower()
        quality_matches = sum(1 for indicator in quality_indicators if indicator in content_lower)
        value_score += min(quality_matches * 0.3, 1.5)
        
        # Twitter/Threads specific bonuses
        if platform in ['twitter', 'threads']:
            # Thread continuation bonus
            if any(word in content_lower for word in ['thread', '1/', '2/', 'continued']):
                value_score += 0.5
            
            # Expert indicators (bio mentions, credentials)
            if any(word in content_lower for word in ['phd', 'professor', 'researcher', 'expert', 'author']):
                value_score += 0.8
        
        # Detect insight types
        insight_type = self._classify_comment_type(content, platform)
        
        return {
            "author": author,
            "author_handle": comment.get('author_handle', ''),
            "content": content[:300] + "..." if len(content) > 300 else content,
            "score": score,
            "value_score": min(value_score, 10.0),
            "insight_type": insight_type,
            "is_op": is_op,
            "url": comment.get('url', ''),
            "created_at": comment.get('created_at', ''),
            "platform": platform,
            "likes": comment.get('likes', 0),
            "retweets": comment.get('retweets', 0) if platform == 'twitter' else comment.get('reposts', 0)
        }
    
    def _classify_comment_type(self, content: str, platform: str = 'reddit') -> str:
        """Classify the type of insight this comment provides"""
        content_lower = content.lower()
        
        # Platform-specific classifications
        if platform in ['twitter', 'threads']:
            if any(word in content_lower for word in ['thread', '1/', '2/', 'continued', 'more in thread']):
                return "Thread Continuation"
            elif any(word in content_lower for word in ['breaking', 'update', 'news', 'just in']):
                return "News Update"
            elif any(word in content_lower for word in ['fact check', 'correction', 'actually', 'wrong']):
                return "Fact Check"
            elif any(word in content_lower for word in ['context', 'background', 'for those who']):
                return "Context/Background"
        
        # Universal classifications
        if any(word in content_lower for word in ['experience', 'happened to me', 'i did', 'when i']):
            return "Personal Experience"
        elif any(word in content_lower for word in ['explanation', 'because', 'reason', 'let me explain']):
            return "Explanation"
        elif any(word in content_lower for word in ['solution', 'fix', 'try this', 'recommend', 'suggestion']):
            return "Solution/Advice"
        elif any(word in content_lower for word in ['alternative', 'another way', 'instead', 'better approach']):
            return "Alternative Approach"
        elif any(word in content_lower for word in ['source', 'study', 'research', 'data', 'link', 'paper']):
            return "Evidence/Source"
        elif any(word in content_lower for word in ['correction', 'wrong', 'mistake', 'misinformation']):
            return "Correction"
        elif any(word in content_lower for word in ['expert', 'professional', 'industry', 'work in']):
            return "Expert Insight"
        else:
            return "Discussion"
    
    def _generate_comment_summary(self, comments: List[Dict], insights: List[Dict]) -> str:
        """Generate a summary of the comment discussion"""
        if not comments:
            return "No comments available"
        
        total_comments = len(comments)
        valuable_insights = len(insights)
        
        if valuable_insights == 0:
            return f"Discussion with {total_comments} comments but limited valuable insights"
        
        # Get insight types
        insight_types = [insight['insight_type'] for insight in insights]
        type_counts = {}
        for itype in insight_types:
            type_counts[itype] = type_counts.get(itype, 0) + 1
        
        # Create summary
        if valuable_insights == 1:
            return f"Discussion includes valuable {insights[0]['insight_type'].lower()}"
        elif valuable_insights <= 3:
            types_str = ", ".join(type_counts.keys())
            return f"Discussion with {valuable_insights} valuable insights: {types_str}"
        else:
            top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:2]
            types_str = ", ".join([t[0] for t in top_types])
            return f"Rich discussion with {valuable_insights} insights including {types_str}"
    
    def get_comment_highlights(self, post_id: str) -> Optional[Dict]:
        """Get cached comment highlights for a post"""
        for analysis in self.analysis_cache.values():
            if post_id in str(analysis):
                return analysis
        return None