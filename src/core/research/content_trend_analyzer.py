#!/usr/bin/env python3
"""
Content Trend Analyzer for PrisMind - Modular Implementation
Handles trend analysis and content gap detection
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta

from .trend_analysis import TrendAnalysis
from .content_gap_analysis import ContentGapAnalysis


class ContentTrendAnalyzer:
    """Handles trend analysis and content gap detection"""
    
    def __init__(self):
        self.trend_analysis = TrendAnalysis()
        self.gap_analysis = ContentGapAnalysis()
    
    def analyze_trends(self, contents: List[Dict[str, Any]], time_window_days: int = 30) -> Dict[str, Any]:
        """Analyze trends in content over time"""
        if not contents:
            return {
                'trending_topics': [],
                'trending_authors': [],
                'platform_distribution': {},
                'sentiment_trends': {},
                'engagement_trends': {},
                'time_period': f'{time_window_days} days'
            }
        
        # Filter content by time window
        filtered_contents = self._filter_by_time_window(contents, time_window_days)
        
        # Analyze trends
        trending_topics = self.trend_analysis.analyze_trending_topics(filtered_contents)
        trending_authors = self.trend_analysis.analyze_trending_authors(filtered_contents)
        platform_distribution = self.trend_analysis.analyze_platform_distribution(filtered_contents)
        sentiment_trends = self.trend_analysis.analyze_sentiment_trends(filtered_contents)
        engagement_trends = self.trend_analysis.analyze_engagement_trends(filtered_contents)
        
        return {
            'trending_topics': trending_topics,
            'trending_authors': trending_authors,
            'platform_distribution': platform_distribution,
            'sentiment_trends': sentiment_trends,
            'engagement_trends': engagement_trends,
            'time_period': f'{time_window_days} days',
            'total_content_analyzed': len(filtered_contents)
        }
    
    def find_content_gaps(self, contents: List[Dict[str, Any]], target_areas: List[str] = None) -> Dict[str, Any]:
        """Find content gaps in the collection"""
        if not contents:
            return {
                'missing_topics': target_areas or [],
                'underrepresented_authors': [],
                'platform_gaps': {},
                'quality_gaps': [],
                'recommendations': []
            }
        
        # Find gaps
        missing_topics = self.gap_analysis.find_missing_topics(contents, target_areas)
        underrepresented_authors = self.gap_analysis.find_underrepresented_authors(contents)
        platform_gaps = self.gap_analysis.analyze_platform_gaps(contents)
        quality_gaps = self.gap_analysis.find_quality_gaps(contents)
        
        # Generate recommendations
        recommendations = self.gap_analysis.generate_gap_recommendations(
            missing_topics, underrepresented_authors, platform_gaps, quality_gaps
        )
        
        return {
            'missing_topics': missing_topics,
            'underrepresented_authors': underrepresented_authors,
            'platform_gaps': platform_gaps,
            'quality_gaps': quality_gaps,
            'recommendations': recommendations,
            'total_content_analyzed': len(contents)
        }
    
    def _filter_by_time_window(self, contents: List[Dict[str, Any]], time_window_days: int) -> List[Dict[str, Any]]:
        """Filter content by time window"""
        if not contents:
            return []
        
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        filtered_contents = []
        
        for content in contents:
            created_at = content.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        content_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        content_date = created_at
                    
                    if content_date >= cutoff_date:
                        filtered_contents.append(content)
                except:
                    # If date parsing fails, include the content
                    filtered_contents.append(content)
            else:
                # If no date, include the content
                filtered_contents.append(content)
        
        return filtered_contents