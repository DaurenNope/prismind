"""
Smart Content Organizer - Creates intelligent tables and views
"""
import pandas as pd
import json
from typing import Dict, List, Any
from collections import defaultdict, Counter
import sqlite3
from pathlib import Path

class SmartOrganizer:
    """Creates smart tables and organized views of content"""
    
    def __init__(self, db_path="data/prismind.db"):
        self.db_path = Path(db_path)
    
    def get_tools_by_category(self) -> Dict[str, List[Dict]]:
        """Organize tools by category"""
        with sqlite3.connect(self.db_path) as conn:
            tools_df = pd.read_sql_query("""
                SELECT post_id, author, smart_title, content, smart_tags, value_score, url, category, topic
                FROM posts 
                WHERE (content_type LIKE '%Tool%' OR content_type LIKE '%App%' OR content_type LIKE '%Software%')
                AND is_deleted = 0
                ORDER BY value_score DESC
            """, conn)
        
        if tools_df.empty:
            return {}
        
        # Categorize tools
        categories = defaultdict(list)
        
        for _, row in tools_df.iterrows():
            tool_info = {
                'title': row['smart_title'] or row['content'][:100],
                'author': row['author'],
                'value_score': row['value_score'],
                'url': row['url'],
                'post_id': row['post_id']
            }
            
            # Extract tags for categorization
            tags = []
            try:
                if row['smart_tags']:
                    tags = json.loads(row['smart_tags']) if isinstance(row['smart_tags'], str) else row['smart_tags']
            except:
                pass
            
            # Smart categorization based on tags and content
            category = self._categorize_tool(row['content'], tags, row['topic'])
            categories[category].append(tool_info)
        
        # Sort each category by value score
        for category in categories:
            categories[category] = sorted(categories[category], key=lambda x: x['value_score'], reverse=True)
        
        return dict(categories)
    
    def get_opinions_by_topic(self) -> Dict[str, List[Dict]]:
        """Organize opinions and insights by topic"""
        with sqlite3.connect(self.db_path) as conn:
            opinions_df = pd.read_sql_query("""
                SELECT post_id, author, smart_title, content, smart_tags, value_score, url, topic
                FROM posts 
                WHERE (content_type LIKE '%Opinion%' OR content_type LIKE '%Insight%' OR content_type LIKE '%Analysis%')
                AND is_deleted = 0
                ORDER BY value_score DESC
            """, conn)
        
        if opinions_df.empty:
            return {}
        
        topics = defaultdict(list)
        
        for _, row in opinions_df.iterrows():
            opinion_info = {
                'title': row['smart_title'] or row['content'][:100],
                'author': row['author'],
                'value_score': row['value_score'],
                'url': row['url'],
                'post_id': row['post_id']
            }
            
            # Group by topic or infer from content
            topic = row['topic'] or self._infer_topic(row['content'])
            topics[topic].append(opinion_info)
        
        # Sort each topic by value score
        for topic in topics:
            topics[topic] = sorted(topics[topic], key=lambda x: x['value_score'], reverse=True)
        
        return dict(topics)
    
    def get_learning_resources_by_level(self) -> Dict[str, List[Dict]]:
        """Organize learning resources by complexity level"""
        with sqlite3.connect(self.db_path) as conn:
            learning_df = pd.read_sql_query("""
                SELECT post_id, author, smart_title, content, smart_tags, value_score, url, complexity_level
                FROM posts 
                WHERE (content_type LIKE '%Tutorial%' OR content_type LIKE '%Guide%' OR content_type LIKE '%Course%')
                AND is_deleted = 0
                ORDER BY value_score DESC
            """, conn)
        
        if learning_df.empty:
            return {}
        
        levels = {
            'Beginner': [],
            'Intermediate': [],
            'Advanced': [],
            'Expert': []
        }
        
        for _, row in learning_df.iterrows():
            resource_info = {
                'title': row['smart_title'] or row['content'][:100],
                'author': row['author'],
                'value_score': row['value_score'],
                'url': row['url'],
                'post_id': row['post_id']
            }
            
            # Determine complexity level
            level = row['complexity_level'] or self._infer_complexity(row['content'])
            if level in levels:
                levels[level].append(resource_info)
            else:
                levels['Intermediate'].append(resource_info)  # Default
        
        # Remove empty levels and sort
        return {level: sorted(resources, key=lambda x: x['value_score'], reverse=True) 
                for level, resources in levels.items() if resources}
    
    def get_author_collections(self, min_posts=3) -> Dict[str, List[Dict]]:
        """Create collections by prolific authors"""
        with sqlite3.connect(self.db_path) as conn:
            author_df = pd.read_sql_query("""
                SELECT author, COUNT(*) as post_count, AVG(value_score) as avg_score
                FROM posts 
                WHERE is_deleted = 0 AND author IS NOT NULL
                GROUP BY author
                HAVING post_count >= ?
                ORDER BY avg_score DESC, post_count DESC
            """, conn, params=(min_posts,))
        
        collections = {}
        
        for _, author_row in author_df.iterrows():
            author = author_row['author']
            posts_df = pd.read_sql_query("""
                SELECT post_id, smart_title, content, value_score, url, content_type
                FROM posts 
                WHERE author = ? AND is_deleted = 0
                ORDER BY value_score DESC
                LIMIT 10
            """, conn, params=(author,))
            
            posts = []
            for _, post in posts_df.iterrows():
                posts.append({
                    'title': post['smart_title'] or post['content'][:100],
                    'value_score': post['value_score'],
                    'url': post['url'],
                    'content_type': post['content_type'],
                    'post_id': post['post_id']
                })
            
            collections[f"{author} ({author_row['post_count']} posts, {author_row['avg_score']:.1f}⭐)"] = posts
        
        return collections
    
    def get_trending_topics(self, days=30) -> List[Dict]:
        """Get trending topics based on recent activity"""
        with sqlite3.connect(self.db_path) as conn:
            recent_df = pd.read_sql_query("""
                SELECT smart_tags, topic, value_score
                FROM posts 
                WHERE is_deleted = 0 
                AND datetime(created_timestamp) >= datetime('now', '-{} days')
            """.format(days), conn)
        
        if recent_df.empty:
            return []
        
        # Count tag frequencies
        tag_counts = Counter()
        topic_counts = Counter()
        tag_scores = defaultdict(list)
        topic_scores = defaultdict(list)
        
        for _, row in recent_df.iterrows():
            # Process tags
            try:
                if row['smart_tags']:
                    tags = json.loads(row['smart_tags']) if isinstance(row['smart_tags'], str) else row['smart_tags']
                    for tag in tags:
                        tag_counts[tag] += 1
                        tag_scores[tag].append(row['value_score'] or 0)
            except:
                pass
            
            # Process topics
            if row['topic']:
                topic_counts[row['topic']] += 1
                topic_scores[row['topic']].append(row['value_score'] or 0)
        
        # Calculate trending score (frequency × average value)
        trending = []
        
        for tag, count in tag_counts.most_common(20):
            avg_score = sum(tag_scores[tag]) / len(tag_scores[tag])
            trending_score = count * avg_score
            trending.append({
                'name': tag,
                'type': 'tag',
                'count': count,
                'avg_score': avg_score,
                'trending_score': trending_score
            })
        
        for topic, count in topic_counts.most_common(10):
            avg_score = sum(topic_scores[topic]) / len(topic_scores[topic])
            trending_score = count * avg_score
            trending.append({
                'name': topic,
                'type': 'topic',
                'count': count,
                'avg_score': avg_score,
                'trending_score': trending_score
            })
        
        return sorted(trending, key=lambda x: x['trending_score'], reverse=True)[:15]
    
    def _categorize_tool(self, content: str, tags: List[str], topic: str) -> str:
        """Smart tool categorization"""
        content_lower = content.lower()
        all_tags_lower = [tag.lower() for tag in tags]
        
        # AI/ML Tools
        if any(keyword in content_lower for keyword in ['ai', 'machine learning', 'gpt', 'llm', 'chatbot', 'claude', 'gemini']):
            return 'AI & Machine Learning'
        
        # Development Tools
        if any(keyword in content_lower for keyword in ['code', 'programming', 'api', 'github', 'deployment', 'docker']):
            return 'Development & Coding'
        
        # Design Tools
        if any(keyword in content_lower for keyword in ['design', 'ui', 'ux', 'figma', 'canva', 'image', 'visual']):
            return 'Design & Visual'
        
        # Productivity Tools
        if any(keyword in content_lower for keyword in ['productivity', 'automation', 'workflow', 'task', 'calendar', 'notes']):
            return 'Productivity & Automation'
        
        # Marketing Tools
        if any(keyword in content_lower for keyword in ['marketing', 'social media', 'analytics', 'seo', 'email']):
            return 'Marketing & Analytics'
        
        # Writing Tools
        if any(keyword in content_lower for keyword in ['writing', 'editor', 'grammar', 'content', 'blog']):
            return 'Writing & Content'
        
        # Browser/Web Tools
        if any(keyword in content_lower for keyword in ['browser', 'extension', 'web', 'chrome', 'firefox']):
            return 'Browser & Web'
        
        return 'Other Tools'
    
    def _infer_topic(self, content: str) -> str:
        """Infer topic from content"""
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ['startup', 'business', 'entrepreneur', 'funding']):
            return 'Startup & Business'
        elif any(keyword in content_lower for keyword in ['ai', 'artificial intelligence', 'machine learning']):
            return 'AI & Technology'
        elif any(keyword in content_lower for keyword in ['productivity', 'efficiency', 'workflow']):
            return 'Productivity'
        elif any(keyword in content_lower for keyword in ['design', 'ui', 'ux', 'creative']):
            return 'Design'
        elif any(keyword in content_lower for keyword in ['programming', 'development', 'coding']):
            return 'Development'
        elif any(keyword in content_lower for keyword in ['marketing', 'growth', 'sales']):
            return 'Marketing & Growth'
        else:
            return 'General'
    
    def _infer_complexity(self, content: str) -> str:
        """Infer complexity level from content"""
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ['beginner', 'intro', 'basics', 'getting started', 'simple']):
            return 'Beginner'
        elif any(keyword in content_lower for keyword in ['advanced', 'expert', 'complex', 'deep dive', 'master']):
            return 'Advanced'
        elif any(keyword in content_lower for keyword in ['intermediate', 'beyond basics', 'next level']):
            return 'Intermediate'
        else:
            return 'Intermediate'  # Default
    
    def create_markdown_tables(self) -> str:
        """Generate markdown tables for export"""
        markdown = "# PrisMind Smart Collections\n\n"
        
        # Tools table
        tools = self.get_tools_by_category()
        if tools:
            markdown += "## 🛠️ Tools by Category\n\n"
            for category, tool_list in tools.items():
                markdown += f"### {category}\n\n"
                markdown += "| Tool | Author | Score | Link |\n"
                markdown += "|------|--------|-------|------|\n"
                for tool in tool_list[:10]:  # Top 10 per category
                    markdown += f"| {tool['title']} | {tool['author']} | {tool['value_score']:.1f}/10 | [Link]({tool['url']}) |\n"
                markdown += "\n"
        
        # Learning resources
        learning = self.get_learning_resources_by_level()
        if learning:
            markdown += "## 📚 Learning Resources by Level\n\n"
            for level, resources in learning.items():
                markdown += f"### {level}\n\n"
                markdown += "| Resource | Author | Score | Link |\n"
                markdown += "|----------|--------|-------|------|\n"
                for resource in resources[:10]:
                    markdown += f"| {resource['title']} | {resource['author']} | {resource['value_score']:.1f}/10 | [Link]({resource['url']}) |\n"
                markdown += "\n"
        
        return markdown