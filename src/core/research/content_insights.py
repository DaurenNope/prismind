#!/usr/bin/env python3
"""
Content Insights for PrisMind
Handles insights generation and recommendations
"""

from typing import List, Dict, Any
from collections import Counter


class ContentInsights:
    """Handles insights generation and recommendations"""
    
    def __init__(self):
        pass
    
    def generate_quality_recommendations(self, avg_quality: float, avg_value: float, 
                                       high_quality_count: int, low_quality_count: int, 
                                       total_count: int) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        if avg_quality < 0.5:
            recommendations.append("Focus on improving content quality - current average is below 50%")
        
        if avg_value < 0.4:
            recommendations.append("Content value is low - consider curating higher-value sources")
        
        if low_quality_count > high_quality_count:
            recommendations.append("More low-quality content than high-quality - review collection sources")
        
        if total_count < 50:
            recommendations.append("Limited content sample - collect more data for better analysis")
        
        if avg_quality > 0.7 and avg_value > 0.6:
            recommendations.append("Excellent content quality - maintain current collection strategy")
        
        return recommendations
    
    def analyze_top_performers(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze top performing content"""
        if not contents:
            return []
        
        # Sort by combined quality and value score
        scored_contents = []
        for content in contents:
            quality_score = content.get('quality_score', 0)
            value_score = content.get('value_score', 0)
            combined_score = (quality_score + value_score) / 2
            
            scored_contents.append({
                'content': content,
                'combined_score': combined_score,
                'quality_score': quality_score,
                'value_score': value_score
            })
        
        # Sort by combined score
        scored_contents.sort(key=lambda x: x['combined_score'], reverse=True)
        
        # Return top 10
        top_performers = []
        for item in scored_contents[:10]:
            content = item['content']
            top_performers.append({
                'title': content.get('smart_title', 'Untitled'),
                'author': content.get('author', 'Unknown'),
                'platform': content.get('platform', 'Unknown'),
                'combined_score': item['combined_score'],
                'quality_score': item['quality_score'],
                'value_score': item['value_score'],
                'url': content.get('url', ''),
                'topic': content.get('topic', 'General')
            })
        
        return top_performers
    
    def analyze_content_patterns(self, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in content"""
        if not contents:
            return {}
        
        # Platform distribution
        platforms = [content.get('platform', 'unknown') for content in contents]
        platform_dist = Counter(platforms)
        
        # Topic distribution
        topics = [content.get('topic', 'general') for content in contents]
        topic_dist = Counter(topics)
        
        # Author distribution
        authors = [content.get('author', 'unknown') for content in contents]
        author_dist = Counter(authors)
        
        # Content type distribution
        content_types = [content.get('content_type', 'unknown') for content in contents]
        type_dist = Counter(content_types)
        
        # Engagement patterns
        engagement_scores = []
        for content in contents:
            engagement = content.get('engagement', {})
            total_engagement = (
                engagement.get('likes', 0) + 
                engagement.get('retweets', 0) + 
                engagement.get('replies', 0)
            )
            engagement_scores.append(total_engagement)
        
        avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0
        
        return {
            'platform_distribution': dict(platform_dist.most_common(5)),
            'topic_distribution': dict(topic_dist.most_common(10)),
            'author_distribution': dict(author_dist.most_common(10)),
            'content_type_distribution': dict(type_dist.most_common(5)),
            'average_engagement': avg_engagement,
            'total_content': len(contents)
        }
    
    def identify_improvement_areas(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify areas for improvement"""
        if not contents:
            return []
        
        improvement_areas = []
        
        # Low-quality content analysis
        low_quality = [c for c in contents if c.get('quality_score', 0) < 0.4]
        if low_quality:
            improvement_areas.append({
                'area': 'Content Quality',
                'issue': f'{len(low_quality)} posts have low quality scores',
                'recommendation': 'Review and improve content curation process',
                'priority': 'high'
            })
        
        # Low-value content analysis
        low_value = [c for c in contents if c.get('value_score', 0) < 0.3]
        if low_value:
            improvement_areas.append({
                'area': 'Content Value',
                'issue': f'{len(low_value)} posts have low value scores',
                'recommendation': 'Focus on collecting higher-value content',
                'priority': 'high'
            })
        
        # Platform diversity
        platforms = set(c.get('platform', 'unknown') for c in contents)
        if len(platforms) < 3:
            improvement_areas.append({
                'area': 'Platform Diversity',
                'issue': f'Only {len(platforms)} platforms represented',
                'recommendation': 'Expand collection to more platforms',
                'priority': 'medium'
            })
        
        # Author diversity
        authors = set(c.get('author', 'unknown') for c in contents)
        if len(authors) < 20:
            improvement_areas.append({
                'area': 'Author Diversity',
                'issue': f'Only {len(authors)} unique authors',
                'recommendation': 'Follow more diverse content creators',
                'priority': 'medium'
            })
        
        # Engagement analysis
        low_engagement = [c for c in contents 
                         if sum(c.get('engagement', {}).values()) < 5]
        if len(low_engagement) > len(contents) * 0.5:
            improvement_areas.append({
                'area': 'Engagement',
                'issue': f'{len(low_engagement)} posts have low engagement',
                'recommendation': 'Focus on more engaging content topics',
                'priority': 'medium'
            })
        
        return improvement_areas
    
    def identify_success_factors(self, contents: List[Dict[str, Any]]) -> List[str]:
        """Identify factors that contribute to success"""
        if not contents:
            return []
        
        success_factors = []
        
        # High-quality content analysis
        high_quality = [c for c in contents if c.get('quality_score', 0) > 0.7]
        if high_quality:
            # Analyze common characteristics
            platforms = [c.get('platform', '') for c in high_quality]
            platform_counter = Counter(platforms)
            top_platform = platform_counter.most_common(1)[0][0]
            
            success_factors.append(f"High-quality content often comes from {top_platform}")
        
        # High-value content analysis
        high_value = [c for c in contents if c.get('value_score', 0) > 0.7]
        if high_value:
            # Analyze topics
            topics = [c.get('topic', '') for c in high_value]
            topic_counter = Counter(topics)
            top_topic = topic_counter.most_common(1)[0][0]
            
            success_factors.append(f"High-value content often focuses on {top_topic}")
        
        # Engagement analysis
        high_engagement = [c for c in contents 
                          if sum(c.get('engagement', {}).values()) > 50]
        if high_engagement:
            # Analyze content types
            content_types = [c.get('content_type', '') for c in high_engagement]
            type_counter = Counter(content_types)
            top_type = type_counter.most_common(1)[0][0]
            
            success_factors.append(f"High-engagement content is often {top_type}")
        
        # Author analysis
        top_authors = Counter(c.get('author', '') for c in contents)
        if top_authors:
            top_author = top_authors.most_common(1)[0][0]
            success_factors.append(f"Content from {top_author} performs well")
        
        return success_factors
    
    def generate_insights_summary(self, top_performers: List[Dict[str, Any]], 
                                content_patterns: Dict[str, Any], 
                                improvement_areas: List[Dict[str, Any]], 
                                success_factors: List[str]) -> str:
        """Generate a comprehensive insights summary"""
        summary = "Content Quality Analysis Summary\n"
        summary += "=" * 40 + "\n\n"
        
        # Top performers
        if top_performers:
            summary += "Top Performing Content:\n"
            for i, performer in enumerate(top_performers[:3], 1):
                summary += f"{i}. {performer['title']} by {performer['author']} "
                summary += f"(Score: {performer['combined_score']:.2f})\n"
            summary += "\n"
        
        # Content patterns
        if content_patterns:
            summary += "Content Patterns:\n"
            platform_dist = content_patterns.get('platform_distribution', {})
            if platform_dist:
                top_platform = max(platform_dist.items(), key=lambda x: x[1])
                summary += f"- Most content from {top_platform[0]} ({top_platform[1]} posts)\n"
            
            topic_dist = content_patterns.get('topic_distribution', {})
            if topic_dist:
                top_topic = max(topic_dist.items(), key=lambda x: x[1])
                summary += f"- Most common topic: {top_topic[0]} ({top_topic[1]} posts)\n"
            
            summary += f"- Average engagement: {content_patterns.get('average_engagement', 0):.1f}\n"
            summary += "\n"
        
        # Success factors
        if success_factors:
            summary += "Success Factors:\n"
            for factor in success_factors[:3]:
                summary += f"- {factor}\n"
            summary += "\n"
        
        # Improvement areas
        if improvement_areas:
            summary += "Areas for Improvement:\n"
            for area in improvement_areas[:3]:
                summary += f"- {area['area']}: {area['issue']}\n"
                summary += f"  Recommendation: {area['recommendation']}\n"
            summary += "\n"
        
        return summary





