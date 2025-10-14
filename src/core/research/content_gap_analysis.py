#!/usr/bin/env python3
"""
Content Gap Analysis for PrisMind
Handles content gap detection and recommendations
"""

from typing import List, Dict, Any
from collections import Counter, defaultdict


class ContentGapAnalysis:
    """Handles content gap detection and recommendations"""
    
    def __init__(self):
        pass
    
    def find_missing_topics(self, contents: List[Dict[str, Any]], target_areas: List[str] = None) -> List[str]:
        """Find missing topics in content collection"""
        if not contents:
            return target_areas or []
        
        # Extract all topics from existing content
        existing_topics = set()
        for content in contents:
            # From title
            title = content.get('title', '')
            if title:
                existing_topics.update(self._extract_keywords(title))
            
            # From content
            content_text = content.get('content', '')
            if content_text:
                existing_topics.update(self._extract_keywords(content_text))
            
            # From tags
            tags = content.get('tags', [])
            if isinstance(tags, list):
                existing_topics.update(tags)
            
            # From categories
            categories = content.get('categories', [])
            if isinstance(categories, list):
                existing_topics.update(categories)
        
        # Find missing topics
        if target_areas:
            missing_topics = [area for area in target_areas if area.lower() not in existing_topics]
        else:
            # Define common target areas if none provided
            common_areas = [
                'artificial intelligence', 'machine learning', 'data science',
                'web development', 'mobile development', 'devops', 'cloud computing',
                'cybersecurity', 'blockchain', 'cryptocurrency', 'fintech',
                'healthtech', 'edtech', 'ecommerce', 'saas', 'startups',
                'product management', 'design', 'marketing', 'sales',
                'leadership', 'entrepreneurship', 'innovation', 'technology trends'
            ]
            missing_topics = [area for area in common_areas if area.lower() not in existing_topics]
        
        return missing_topics
    
    def find_underrepresented_authors(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find underrepresented authors in content collection"""
        if not contents:
            return []
        
        # Count posts by author
        author_counts = Counter()
        author_engagement = defaultdict(list)
        
        for content in contents:
            author = content.get('author', '')
            if author:
                author_counts[author] += 1
                
                # Track engagement for this author
                engagement = content.get('engagement', {})
                total_engagement = (
                    engagement.get('likes', 0) + 
                    engagement.get('retweets', 0) + 
                    engagement.get('replies', 0)
                )
                author_engagement[author].append(total_engagement)
        
        # Find underrepresented authors (those with few posts but high engagement)
        underrepresented_authors = []
        total_posts = len(contents)
        avg_posts_per_author = total_posts / len(author_counts) if author_counts else 0
        
        for author, post_count in author_counts.items():
            if post_count < avg_posts_per_author * 0.5:  # Less than half the average
                avg_engagement = sum(author_engagement[author]) / len(author_engagement[author])
                if avg_engagement > 10:  # High engagement threshold
                    underrepresented_authors.append({
                        'author': author,
                        'post_count': post_count,
                        'average_engagement': avg_engagement,
                        'recommendation': 'Increase content from this high-engagement author'
                    })
        
        return underrepresented_authors
    
    def analyze_platform_gaps(self, contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze platform gaps in content collection"""
        if not contents:
            return {}
        
        # Count content by platform
        platform_counts = Counter()
        platform_engagement = defaultdict(list)
        
        for content in contents:
            platform = content.get('platform', 'unknown')
            platform_counts[platform] += 1
            
            # Track engagement by platform
            engagement = content.get('engagement', {})
            total_engagement = (
                engagement.get('likes', 0) + 
                engagement.get('retweets', 0) + 
                engagement.get('replies', 0)
            )
            platform_engagement[platform].append(total_engagement)
        
        # Analyze platform gaps
        total_content = len(contents)
        platform_gaps = {}
        
        # Define target platforms
        target_platforms = ['twitter', 'reddit', 'linkedin', 'github', 'medium', 'dev.to']
        
        for platform in target_platforms:
            count = platform_counts.get(platform, 0)
            percentage = (count / total_content) * 100 if total_content > 0 else 0
            
            if count > 0:
                avg_engagement = sum(platform_engagement[platform]) / len(platform_engagement[platform])
            else:
                avg_engagement = 0
            
            platform_gaps[platform] = {
                'count': count,
                'percentage': percentage,
                'average_engagement': avg_engagement,
                'gap_status': 'underrepresented' if percentage < 10 else 'adequate' if percentage < 30 else 'overrepresented'
            }
        
        return platform_gaps
    
    def find_quality_gaps(self, contents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find quality gaps in content collection"""
        if not contents:
            return []
        
        quality_gaps = []
        
        # Analyze content length distribution
        content_lengths = [len(content.get('content', '')) for content in contents]
        if content_lengths:
            avg_length = sum(content_lengths) / len(content_lengths)
            short_content = sum(1 for length in content_lengths if length < avg_length * 0.5)
            if short_content > len(contents) * 0.3:
                quality_gaps.append({
                    'type': 'content_length',
                    'issue': f'{short_content} posts are too short (less than 50% of average)',
                    'recommendation': 'Focus on creating longer, more detailed content'
                })
        
        # Analyze engagement quality
        low_engagement_count = 0
        for content in contents:
            engagement = content.get('engagement', {})
            total_engagement = (
                engagement.get('likes', 0) + 
                engagement.get('retweets', 0) + 
                engagement.get('replies', 0)
            )
            if total_engagement < 5:
                low_engagement_count += 1
        
        if low_engagement_count > len(contents) * 0.4:
            quality_gaps.append({
                'type': 'engagement',
                'issue': f'{low_engagement_count} posts have very low engagement',
                'recommendation': 'Improve content quality and relevance to increase engagement'
            })
        
        # Analyze content diversity
        topics = set()
        for content in contents:
            title = content.get('title', '')
            if title:
                topics.update(self._extract_keywords(title))
        
        if len(topics) < 20:
            quality_gaps.append({
                'type': 'diversity',
                'issue': f'Only {len(topics)} unique topics found',
                'recommendation': 'Diversify content topics to cover more areas'
            })
        
        return quality_gaps
    
    def generate_gap_recommendations(self, missing_topics: List[str], 
                                   underrepresented_authors: List[Dict[str, Any]], 
                                   platform_gaps: Dict[str, Any], 
                                   quality_gaps: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on gap analysis"""
        recommendations = []
        
        # Topic recommendations
        if missing_topics:
            recommendations.append(f"Consider creating content about: {', '.join(missing_topics[:5])}")
        
        # Author recommendations
        if underrepresented_authors:
            recommendations.append(f"Engage more with high-quality authors: {', '.join([a['author'] for a in underrepresented_authors[:3]])}")
        
        # Platform recommendations
        underrepresented_platforms = [p for p, data in platform_gaps.items() if data['gap_status'] == 'underrepresented']
        if underrepresented_platforms:
            recommendations.append(f"Expand presence on: {', '.join(underrepresented_platforms)}")
        
        # Quality recommendations
        for gap in quality_gaps:
            recommendations.append(gap['recommendation'])
        
        return recommendations
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        if not text:
            return []
        
        # Simple keyword extraction
        words = text.lower().split()
        
        # Filter out common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
        
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Remove duplicates and return
        return list(set(keywords))





