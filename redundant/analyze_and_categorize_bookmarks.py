#!/usr/bin/env python3
"""
Analyze and categorize existing bookmarks into the three-table system
"""

import pandas as pd
from pathlib import Path
from multi_table_manager import MultiTableManager
from scripts.database_manager import DatabaseManager
import re
from typing import Dict, List, Any, Optional

class BookmarkAnalyzer:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.supabase_db = MultiTableManager()
        
    def get_existing_bookmarks(self) -> pd.DataFrame:
        """Get all existing bookmarks using DatabaseManager"""
        # Using DatabaseManager instead of direct SQLite connection
        posts_df = self.db_manager.get_all_posts()
        
        # Filter for non-deleted posts and add curation info
        if not posts_df.empty:
            # Filter for non-deleted posts (already done in get_all_posts by default)
            non_deleted_posts = posts_df[posts_df['is_deleted'] == 0] if 'is_deleted' in posts_df.columns else posts_df
            
            # Add curation information (simulating the LEFT JOIN)
            # In a real implementation, we would join with curation data
            # For now, we'll just add empty columns for compatibility
            if 'use_case' not in non_deleted_posts.columns:
                non_deleted_posts['use_case'] = None
            if 'curation_status' not in non_deleted_posts.columns:
                non_deleted_posts['curation_status'] = None
            if 'curation_notes' not in non_deleted_posts.columns:
                non_deleted_posts['curation_notes'] = None
                
            return non_deleted_posts.sort_values('created_timestamp', ascending=False) if 'created_timestamp' in non_deleted_posts.columns else non_deleted_posts
        
        # Return empty DataFrame with expected columns if no posts
        return pd.DataFrame(columns=['use_case', 'curation_status', 'curation_notes'])
    
    def analyze_content(self, content: str, title: str = "", author: str = "") -> Dict[str, Any]:
        """Analyze content to determine category and quality"""
        full_text = f"{title} {content}".lower()
        
        # Programming indicators
        programming_keywords = [
            'code', 'programming', 'javascript', 'python', 'react', 'vue', 'angular',
            'framework', 'library', 'api', 'database', 'sql', 'git', 'docker',
            'tutorial', 'how to', 'implementation', 'function', 'class', 'component',
            'algorithm', 'data structure', 'optimization', 'performance', 'debug',
            'testing', 'unit test', 'integration', 'deployment', 'ci/cd'
        ]
        
        # Research indicators
        research_keywords = [
            'study', 'research', 'analysis', 'data', 'statistics', 'survey',
            'report', 'findings', 'evidence', 'scientific', 'peer-reviewed',
            'journal', 'paper', 'thesis', 'investigation', 'examination',
            'fact-check', 'verify', 'validate', 'credibility', 'source'
        ]
        
        # Copywriting indicators
        copywriting_keywords = [
            'social media', 'marketing', 'copywriting', 'content creation',
            'brand', 'engagement', 'viral', 'trending', 'influencer',
            'post', 'tweet', 'thread', 'story', 'reel', 'video',
            'caption', 'hashtag', 'call to action', 'cta', 'conversion'
        ]
        
        # Marketing/spam indicators (to filter out)
        spam_keywords = [
            'buy now', 'limited time', 'act fast', 'don\'t miss out',
            'exclusive offer', 'discount', 'sale', 'promotion', 'deal',
            'click here', 'sign up now', 'free trial', 'subscribe',
            'make money', 'earn cash', 'work from home', 'get rich'
        ]
        
        # Count keyword matches
        programming_score = sum(1 for keyword in programming_keywords if keyword in full_text)
        research_score = sum(1 for keyword in research_keywords if keyword in full_text)
        copywriting_score = sum(1 for keyword in copywriting_keywords if keyword in full_text)
        spam_score = sum(1 for keyword in spam_keywords if keyword in full_text)
        
        # Determine category based on highest score
        scores = {
            'programming': programming_score,
            'research': research_score,
            'copywriting': copywriting_score
        }
        
        max_score = max(scores.values())
        category = max(scores, key=scores.get) if max_score > 0 else 'uncertain'
        
        # Quality assessment
        quality_score = 0
        if len(content) > 100:  # Substantial content
            quality_score += 2
        if author and len(author) > 0:  # Has author
            quality_score += 1
        if title and len(title) > 10:  # Has meaningful title
            quality_score += 1
        
        # Penalize for spam indicators
        if spam_score > 2:
            quality_score -= 5
            category = 'spam'
        
        return {
            'category': category,
            'quality_score': quality_score,
            'programming_score': programming_score,
            'research_score': research_score,
            'copywriting_score': copywriting_score,
            'spam_score': spam_score,
            'confidence': max_score / (sum(scores.values()) + 1)  # Confidence in categorization
        }
    
    def categorize_bookmarks(self):
        """Main function to categorize all bookmarks"""
        print("🔍 Analyzing existing bookmarks...")
        
        # Get existing bookmarks
        bookmarks_df = self.get_existing_bookmarks()
        
        if bookmarks_df.empty:
            print("❌ No bookmarks found in database")
            return
        
        print(f"📊 Found {len(bookmarks_df)} bookmarks to analyze")
        
        # Track categorization results
        results = {
            'programming': [],
            'research': [],
            'copywriting': [],
            'uncertain': [],
            'spam': []
        }
        
        # Analyze each bookmark
        for idx, row in bookmarks_df.iterrows():
            post_id = row['post_id']
            content = row.get('content', '')
            title = row.get('ai_summary', '') or row.get('content', '')[:100]
            author = row.get('author', '')
            platform = row.get('platform', '')
            url = row.get('url', '')
            
            # Analyze the content
            analysis = self.analyze_content(content, title, author)
            
            # Prepare post data
            post_data = {
                'id': int(post_id) if post_id.isdigit() else hash(post_id) % 1000000,
                'title': title[:200] if title else 'Untitled',
                'content': content,
                'platform': platform,
                'author': author,
                'author_handle': f"@{author.lower().replace(' ', '')}" if author else '',
                'url': url,
                'value_score': analysis['quality_score'],
                'smart_tags': f"auto-categorized,{analysis['category']}",
                'ai_summary': f"Auto-categorized as {analysis['category']} with confidence {analysis['confidence']:.2f}",
                'folder_category': analysis['category'],
                'category': analysis['category']
            }
            
            # Add category-specific fields
            if analysis['category'] == 'programming':
                post_data.update({
                    'language': self.extract_language(content),
                    'framework': self.extract_framework(content),
                    'difficulty': self.assess_difficulty(content),
                    'implementation_status': 'not_started'
                })
            elif analysis['category'] == 'research':
                post_data.update({
                    'research_topic': self.extract_research_topic(content),
                    'credibility_score': analysis['quality_score'],
                    'fact_check_status': 'pending',
                    'ai_evaluation': f"Quality score: {analysis['quality_score']}, Spam score: {analysis['spam_score']}"
                })
            elif analysis['category'] == 'copywriting':
                post_data.update({
                    'content_type': self.determine_content_type(content),
                    'target_platform': platform,
                    'tone': self.assess_tone(content),
                    'publish_status': 'draft'
                })
            
            # Store result
            results[analysis['category']].append({
                'original_data': row,
                'analysis': analysis,
                'post_data': post_data
            })
        
        # Display analysis results
        print(f"\n📊 Categorization Results:")
        for category, items in results.items():
            print(f"   {category.capitalize()}: {len(items)} items")
        
        # Process each category
        self.process_category('programming', results['programming'])
        self.process_category('research', results['research'])
        self.process_category('copywriting', results['copywriting'])
        
        # Handle uncertain and spam
        if results['uncertain']:
            print(f"\n❓ {len(results['uncertain'])} items need manual review:")
            for item in results['uncertain'][:5]:  # Show first 5
                print(f"   - {item['original_data']['author']}: {item['original_data']['content'][:60]}...")
        
        if results['spam']:
            print(f"\n🗑️  {len(results['spam'])} low-quality items identified (consider deletion)")
    
    def process_category(self, category: str, items: List[Dict]):
        """Process items for a specific category"""
        if not items:
            return
        
        print(f"\n📝 Processing {len(items)} {category} items...")
        
        success_count = 0
        for item in items:
            try:
                if category == 'programming':
                    result = self.supabase_db.insert_programming_post(item['post_data'])
                elif category == 'research':
                    result = self.supabase_db.insert_research_post(item['post_data'])
                elif category == 'copywriting':
                    result = self.supabase_db.insert_copywriting_post(item['post_data'])
                
                if result:
                    success_count += 1
                    print(f"   ✅ Added: {item['post_data']['title'][:50]}...")
                
            except Exception as e:
                print(f"   ❌ Error adding {category} item: {e}")
        
        print(f"   ✅ Successfully added {success_count}/{len(items)} {category} items")
    
    def extract_language(self, content: str) -> str:
        """Extract programming language from content"""
        languages = ['python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift']
        content_lower = content.lower()
        
        for lang in languages:
            if lang in content_lower:
                return lang
        return 'unknown'
    
    def extract_framework(self, content: str) -> str:
        """Extract framework from content"""
        frameworks = ['react', 'vue', 'angular', 'django', 'flask', 'express', 'spring', 'laravel']
        content_lower = content.lower()
        
        for framework in frameworks:
            if framework in content_lower:
                return framework
        return 'unknown'
    
    def assess_difficulty(self, content: str) -> str:
        """Assess programming difficulty"""
        beginner_keywords = ['tutorial', 'beginner', 'introduction', 'basics', 'getting started']
        advanced_keywords = ['advanced', 'optimization', 'architecture', 'design patterns', 'scaling']
        
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in advanced_keywords):
            return 'advanced'
        elif any(keyword in content_lower for keyword in beginner_keywords):
            return 'beginner'
        else:
            return 'intermediate'
    
    def extract_research_topic(self, content: str) -> str:
        """Extract research topic"""
        topics = ['ai', 'healthcare', 'technology', 'science', 'business', 'economics', 'politics']
        content_lower = content.lower()
        
        for topic in topics:
            if topic in content_lower:
                return topic
        return 'general'
    
    def determine_content_type(self, content: str) -> str:
        """Determine copywriting content type"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['insight', 'thought', 'idea']):
            return 'insight'
        elif any(word in content_lower for word in ['rant', 'opinion', 'view']):
            return 'rant'
        elif any(word in content_lower for word in ['social', 'media', 'post']):
            return 'social_media'
        else:
            return 'general'
    
    def assess_tone(self, content: str) -> str:
        """Assess content tone"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['lol', 'haha', 'funny', 'hilarious']):
            return 'humorous'
        elif any(word in content_lower for word in ['professional', 'business', 'corporate']):
            return 'professional'
        else:
            return 'casual'

if __name__ == "__main__":
    analyzer = BookmarkAnalyzer()
    analyzer.categorize_bookmarks() 