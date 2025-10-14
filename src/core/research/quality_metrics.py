#!/usr/bin/env python3
"""
Quality Metrics for PrisMind
Handles quality calculations and distributions
"""

from typing import List, Dict, Any
from statistics import mean, median


class QualityMetrics:
    """Handles quality calculations and distributions"""
    
    def __init__(self):
        pass
    
    def calculate_quality_distribution(self, quality_scores: List[float]) -> Dict[str, int]:
        """Calculate distribution of quality scores"""
        if not quality_scores:
            return {}
        
        distribution = {
            'excellent': 0,  # 0.8-1.0
            'good': 0,       # 0.6-0.8
            'average': 0,    # 0.4-0.6
            'poor': 0,       # 0.2-0.4
            'very_poor': 0   # 0.0-0.2
        }
        
        for score in quality_scores:
            if score >= 0.8:
                distribution['excellent'] += 1
            elif score >= 0.6:
                distribution['good'] += 1
            elif score >= 0.4:
                distribution['average'] += 1
            elif score >= 0.2:
                distribution['poor'] += 1
            else:
                distribution['very_poor'] += 1
        
        return distribution
    
    def calculate_value_distribution(self, value_scores: List[float]) -> Dict[str, int]:
        """Calculate distribution of value scores"""
        if not value_scores:
            return {}
        
        distribution = {
            'high_value': 0,    # 0.7-1.0
            'medium_value': 0,  # 0.4-0.7
            'low_value': 0      # 0.0-0.4
        }
        
        for score in value_scores:
            if score >= 0.7:
                distribution['high_value'] += 1
            elif score >= 0.4:
                distribution['medium_value'] += 1
            else:
                distribution['low_value'] += 1
        
        return distribution
    
    def calculate_quality_statistics(self, quality_scores: List[float]) -> Dict[str, float]:
        """Calculate quality statistics"""
        if not quality_scores:
            return {
                'mean': 0.0,
                'median': 0.0,
                'min': 0.0,
                'max': 0.0,
                'std_dev': 0.0
            }
        
        return {
            'mean': mean(quality_scores),
            'median': median(quality_scores),
            'min': min(quality_scores),
            'max': max(quality_scores),
            'std_dev': self._calculate_std_dev(quality_scores)
        }
    
    def calculate_value_statistics(self, value_scores: List[float]) -> Dict[str, float]:
        """Calculate value statistics"""
        if not value_scores:
            return {
                'mean': 0.0,
                'median': 0.0,
                'min': 0.0,
                'max': 0.0,
                'std_dev': 0.0
            }
        
        return {
            'mean': mean(value_scores),
            'median': median(value_scores),
            'min': min(value_scores),
            'max': max(value_scores),
            'std_dev': self._calculate_std_dev(value_scores)
        }
    
    def identify_quality_trends(self, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify quality trends over time"""
        if not contents:
            return {}
        
        # Group by time periods (simplified)
        recent_content = []
        older_content = []
        
        for content in contents:
            # Simple time-based grouping (in real implementation, use actual dates)
            if content.get('value_score', 0) > 0.5:  # Mock recent content
                recent_content.append(content)
            else:
                older_content.append(content)
        
        # Calculate trends
        recent_quality = [c.get('quality_score', 0) for c in recent_content]
        older_quality = [c.get('quality_score', 0) for c in older_content]
        
        recent_avg = mean(recent_quality) if recent_quality else 0
        older_avg = mean(older_quality) if older_quality else 0
        
        trend_direction = 'improving' if recent_avg > older_avg else 'declining' if recent_avg < older_avg else 'stable'
        
        return {
            'trend_direction': trend_direction,
            'recent_average': recent_avg,
            'older_average': older_avg,
            'change_percentage': ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        }
    
    def calculate_platform_quality(self, contents: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Calculate quality metrics by platform"""
        if not contents:
            return {}
        
        platform_metrics = {}
        
        for content in contents:
            platform = content.get('platform', 'unknown')
            quality_score = content.get('quality_score', 0)
            value_score = content.get('value_score', 0)
            
            if platform not in platform_metrics:
                platform_metrics[platform] = {
                    'quality_scores': [],
                    'value_scores': [],
                    'count': 0
                }
            
            platform_metrics[platform]['quality_scores'].append(quality_score)
            platform_metrics[platform]['value_scores'].append(value_score)
            platform_metrics[platform]['count'] += 1
        
        # Calculate averages
        for platform, metrics in platform_metrics.items():
            quality_scores = metrics['quality_scores']
            value_scores = metrics['value_scores']
            
            platform_metrics[platform] = {
                'average_quality': mean(quality_scores) if quality_scores else 0,
                'average_value': mean(value_scores) if value_scores else 0,
                'count': metrics['count'],
                'quality_std': self._calculate_std_dev(quality_scores),
                'value_std': self._calculate_std_dev(value_scores)
            }
        
        return platform_metrics
    
    def calculate_author_quality(self, contents: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Calculate quality metrics by author"""
        if not contents:
            return {}
        
        author_metrics = {}
        
        for content in contents:
            author = content.get('author', 'unknown')
            quality_score = content.get('quality_score', 0)
            value_score = content.get('value_score', 0)
            
            if author not in author_metrics:
                author_metrics[author] = {
                    'quality_scores': [],
                    'value_scores': [],
                    'count': 0
                }
            
            author_metrics[author]['quality_scores'].append(quality_score)
            author_metrics[author]['value_scores'].append(value_score)
            author_metrics[author]['count'] += 1
        
        # Calculate averages and filter authors with multiple posts
        filtered_metrics = {}
        for author, metrics in author_metrics.items():
            if metrics['count'] >= 2:  # Only authors with 2+ posts
                quality_scores = metrics['quality_scores']
                value_scores = metrics['value_scores']
                
                filtered_metrics[author] = {
                    'average_quality': mean(quality_scores) if quality_scores else 0,
                    'average_value': mean(value_scores) if value_scores else 0,
                    'count': metrics['count'],
                    'quality_consistency': 1.0 - self._calculate_std_dev(quality_scores),
                    'value_consistency': 1.0 - self._calculate_std_dev(value_scores)
                }
        
        return filtered_metrics
    
    def _calculate_std_dev(self, scores: List[float]) -> float:
        """Calculate standard deviation"""
        if len(scores) < 2:
            return 0.0
        
        mean_score = mean(scores)
        variance = sum((x - mean_score) ** 2 for x in scores) / len(scores)
        return variance ** 0.5





