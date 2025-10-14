"""
Content quality metrics and validation rules
"""

import re
from typing import Dict, Any, List


class ContentQualityMetrics:
    """Metrics for evaluating content quality"""
    
    def __init__(self):
        self.min_content_length = 10
        self.max_content_length = 50000
        self.min_title_length = 3
        self.max_title_length = 500
        self.spam_keywords = [
            'click here', 'buy now', 'limited time', 'act now', 'free money',
            'make money fast', 'work from home', 'get rich quick', 'miracle cure'
        ]
        self.low_quality_patterns = [
            r'^(.)\1{10,}',  # Repeated characters
            r'[A-Z]{20,}',   # Excessive caps
            r'[!]{5,}',      # Excessive exclamation
            r'[\?]{3,}',     # Excessive question marks
        ]
    
    def check_content_length(self, content: str) -> Dict[str, Any]:
        """Check if content length is within acceptable range"""
        length = len(content.strip())
        
        if length < self.min_content_length:
            return {
                'valid': False,
                'score': 0.0,
                'reason': f'Content too short ({length} chars, min {self.min_content_length})'
            }
        elif length > self.max_content_length:
            return {
                'valid': False,
                'score': 0.5,
                'reason': f'Content too long ({length} chars, max {self.max_content_length})'
            }
        else:
            return {
                'valid': True,
                'score': 1.0,
                'reason': f'Content length acceptable ({length} chars)'
            }
    
    def check_title_length(self, title: str) -> Dict[str, Any]:
        """Check if title length is within acceptable range"""
        if not title:
            return {
                'valid': False,
                'score': 0.0,
                'reason': 'Title is empty'
            }
        
        length = len(title.strip())
        
        if length < self.min_title_length:
            return {
                'valid': False,
                'score': 0.0,
                'reason': f'Title too short ({length} chars, min {self.min_title_length})'
            }
        elif length > self.max_title_length:
            return {
                'valid': False,
                'score': 0.5,
                'reason': f'Title too long ({length} chars, max {self.max_title_length})'
            }
        else:
            return {
                'valid': True,
                'score': 1.0,
                'reason': f'Title length acceptable ({length} chars)'
            }
    
    def check_spam_keywords(self, content: str) -> Dict[str, Any]:
        """Check for spam keywords in content"""
        content_lower = content.lower()
        found_keywords = []
        
        for keyword in self.spam_keywords:
            if keyword in content_lower:
                found_keywords.append(keyword)
        
        if found_keywords:
            return {
                'valid': False,
                'score': 0.0,
                'reason': f'Spam keywords found: {", ".join(found_keywords)}'
            }
        else:
            return {
                'valid': True,
                'score': 1.0,
                'reason': 'No spam keywords detected'
            }
    
    def check_low_quality_patterns(self, content: str) -> Dict[str, Any]:
        """Check for low quality patterns in content"""
        found_patterns = []
        
        for pattern in self.low_quality_patterns:
            if re.search(pattern, content):
                found_patterns.append(pattern)
        
        if found_patterns:
            return {
                'valid': False,
                'score': 0.2,
                'reason': f'Low quality patterns found: {len(found_patterns)} patterns'
            }
        else:
            return {
                'valid': True,
                'score': 1.0,
                'reason': 'No low quality patterns detected'
            }
    
    def calculate_meaningful_content_ratio(self, content: str) -> float:
        """Calculate ratio of meaningful content vs total content"""
        if not content:
            return 0.0
        
        # Remove whitespace and common punctuation
        cleaned = re.sub(r'[\s\.,!?;:]+', '', content)
        
        if not cleaned:
            return 0.0
        
        # Count meaningful characters (letters, numbers, meaningful symbols)
        meaningful_chars = len(re.findall(r'[a-zA-Z0-9]', cleaned))
        total_chars = len(cleaned)
        
        if total_chars == 0:
            return 0.0
        
        return meaningful_chars / total_chars
    
    def get_quality_score(self, content: str, title: str = None) -> Dict[str, Any]:
        """Get overall quality score for content"""
        scores = []
        issues = []
        
        # Check content length
        content_check = self.check_content_length(content)
        scores.append(content_check['score'])
        if not content_check['valid']:
            issues.append(content_check['reason'])
        
        # Check title if provided
        if title:
            title_check = self.check_title_length(title)
            scores.append(title_check['score'])
            if not title_check['valid']:
                issues.append(title_check['reason'])
        
        # Check for spam keywords
        spam_check = self.check_spam_keywords(content)
        scores.append(spam_check['score'])
        if not spam_check['valid']:
            issues.append(spam_check['reason'])
        
        # Check for low quality patterns
        pattern_check = self.check_low_quality_patterns(content)
        scores.append(pattern_check['score'])
        if not pattern_check['valid']:
            issues.append(pattern_check['reason'])
        
        # Calculate meaningful content ratio
        meaningful_ratio = self.calculate_meaningful_content_ratio(content)
        scores.append(meaningful_ratio)
        
        # Calculate overall score
        overall_score = sum(scores) / len(scores)
        
        return {
            'score': overall_score,
            'meaningful_ratio': meaningful_ratio,
            'issues': issues,
            'valid': overall_score >= 0.6 and len(issues) <= 2
        }





