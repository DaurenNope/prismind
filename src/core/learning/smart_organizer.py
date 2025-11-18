"""
Smart Content Organizer - Creates intelligent tables and views
"""

import json
from pathlib import Path
from typing import Dict, List

from .content_organizer import ContentOrganizer


class SmartOrganizer:
    """Creates smart tables and organized views of content"""

    def __init__(self, db_path="data/beyondlines.db"):
        self.db_path = Path(db_path)
        self.organizer = ContentOrganizer(db_path)

    def get_tools_by_category(self) -> Dict[str, List[Dict]]:
        """Organize tools by category"""
        return self.organizer.get_tools_by_category()

    def get_opinions_by_topic(self) -> Dict[str, List[Dict]]:
        """Organize opinions by topic"""
        return self.organizer.get_opinions_by_topic()

    def get_learning_resources_by_level(self) -> Dict[str, List[Dict]]:
        """Organize learning resources by complexity level"""
        return self.organizer.get_learning_resources_by_level()

    def get_author_collections(self, min_posts=3) -> Dict[str, List[Dict]]:
        """Get collections of posts by author"""
        return self.organizer.get_author_collections(min_posts)

    def get_trending_topics(self, days=30) -> List[Dict]:
        """Get trending topics based on recent activity"""
        return self.organizer.get_trending_topics(days)

    def create_markdown_tables(self) -> str:
        """Create markdown tables for organized content"""
        markdown = "# BEYONDLINES Content Organization\n\n"

        # Tools by category
        tools = self.get_tools_by_category()
        if tools:
            markdown += "## Tools by Category\n\n"
            for category, tool_list in tools.items():
                markdown += f"### {category}\n\n"
                markdown += "| Title | Author | Score | Topic |\n"
                markdown += "|-------|--------|-------|-------|\n"
                for tool in tool_list[:5]:  # Show top 5
                    markdown += f"| {tool['title']} | {tool['author']} | {tool['value_score']:.2f} | {tool['topic']} |\n"
                markdown += "\n"

        # Opinions by topic
        opinions = self.get_opinions_by_topic()
        if opinions:
            markdown += "## Opinions by Topic\n\n"
            for topic, opinion_list in opinions.items():
                markdown += f"### {topic}\n\n"
                markdown += "| Title | Author | Score |\n"
                markdown += "|-------|--------|-------|\n"
                for opinion in opinion_list[:3]:  # Show top 3
                    markdown += f"| {opinion['title']} | {opinion['author']} | {opinion['value_score']:.2f} |\n"
                markdown += "\n"

        # Learning resources by level
        resources = self.get_learning_resources_by_level()
        if resources:
            markdown += "## Learning Resources by Level\n\n"
            for level, resource_list in resources.items():
                markdown += f"### {level}\n\n"
                markdown += "| Title | Author | Score | Topic |\n"
                markdown += "|-------|--------|-------|-------|\n"
                for resource in resource_list[:5]:  # Show top 5
                    markdown += f"| {resource['title']} | {resource['author']} | {resource['value_score']:.2f} | {resource['topic']} |\n"
                markdown += "\n"

        # Trending topics
        trending = self.get_trending_topics()
        if trending:
            markdown += "## Trending Topics\n\n"
            markdown += "| Topic | Posts | Avg Score |\n"
            markdown += "|-------|-------|----------|\n"
            for topic in trending[:10]:  # Show top 10
                markdown += f"| {topic['topic']} | {topic['post_count']} | {topic['avg_score']:.2f} |\n"
            markdown += "\n"

        return markdown
