#!/usr/bin/env python3
"""
Content Quality Analyzer for PrisMind - Modular Implementation
Handles quality analysis and insights generation
"""

from typing import List, Dict, Any

from .quality_metrics import QualityMetrics
from .content_insights import ContentInsights


class ContentQualityAnalyzer:
    """Handles content quality analysis and insights generation"""
    
    def __init__(self):
        self.quality_metrics = QualityMetrics()
        self.content_insights = ContentInsights()
    
    def analyze_content_quality(self, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze overall content quality"""
        if not contents:
            return {
                'average_quality': 0,
                'average_value': 0,
                'quality_distribution': {},
                'high_quality_count': 0,
                'low_quality_count': 0,
                'recommendations': []
            }
        
        # Extract quality and value scores
        quality_scores = [content.get('quality_score', 0) for content in contents]
        value_scores = [content.get('value_score', 0) for content in contents]
        
        # Calculate averages
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        avg_value = sum(value_scores) / len(value_scores) if value_scores else 0
        
        # Calculate distributions
        quality_distribution = self.quality_metrics.calculate_quality_distribution(quality_scores)
        value_distribution = self.quality_metrics.calculate_value_distribution(value_scores)
        
        # Count high and low quality content
        high_quality_count = quality_distribution.get('excellent', 0) + quality_distribution.get('good', 0)
        low_quality_count = quality_distribution.get('poor', 0) + quality_distribution.get('very_poor', 0)
        
        # Generate recommendations
        recommendations = self.content_insights.generate_quality_recommendations(
            avg_quality, avg_value, high_quality_count, low_quality_count, len(contents)
        )
        
        return {
            'average_quality': avg_quality,
            'average_value': avg_value,
            'quality_distribution': quality_distribution,
            'value_distribution': value_distribution,
            'high_quality_count': high_quality_count,
            'low_quality_count': low_quality_count,
            'total_content': len(contents),
            'recommendations': recommendations
        }
    
    def generate_content_insights(self, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive content insights"""
        if not contents:
            return {
                'top_performers': [],
                'content_patterns': {},
                'improvement_areas': [],
                'success_factors': [],
                'insights_summary': 'No content available for analysis'
            }
        
        # Analyze top performers
        top_performers = self.content_insights.analyze_top_performers(contents)
        
        # Analyze content patterns
        content_patterns = self.content_insights.analyze_content_patterns(contents)
        
        # Identify improvement areas
        improvement_areas = self.content_insights.identify_improvement_areas(contents)
        
        # Identify success factors
        success_factors = self.content_insights.identify_success_factors(contents)
        
        # Generate insights summary
        insights_summary = self.content_insights.generate_insights_summary(
            top_performers, content_patterns, improvement_areas, success_factors
        )
        
        return {
            'top_performers': top_performers,
            'content_patterns': content_patterns,
            'improvement_areas': improvement_areas,
            'success_factors': success_factors,
            'insights_summary': insights_summary
        }