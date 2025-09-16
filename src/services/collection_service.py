"""
Collection service for PrisMind
Handles the collection of posts from various platforms
"""
import asyncio
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv

# Import extractors
from src.core.extraction.reddit_extractor import RedditExtractor
from src.core.extraction.twitter_extractor_playwright import TwitterExtractorPlaywright
from src.services.database_manager import get_database_manager

# Load environment variables
load_dotenv()

class CollectionService:
    """Service for managing post collection from various platforms"""
    
    def __init__(self):
        self.db = get_database_manager()
        self.extractors = {
            'twitter': TwitterExtractor(),
            'reddit': RedditExtractor()
        }
        self.collection_stats = {}
    
    async def collect_from_platform(self, platform: str) -> Dict[str, int]:
        """Collect posts from a specific platform"""
        if platform not in self.extractors:
            return {'error': f'Unsupported platform: {platform}'}
        
        extractor = self.extractors[platform]
        stats = {'collected': 0, 'errors': 0}
        
        try:
            # Authenticate with the platform
            if not extractor.authenticate():
                return {'error': f'Failed to authenticate with {platform}'}
            
            # Get saved posts
            posts = extractor.get_saved_posts(limit=50)  # Adjust limit as needed
            
            # Process and save posts
            for post in posts:
                try:
                    # Convert post to dict if it's not already
                    if hasattr(post, 'to_dict'):
                        post_data = post.to_dict()
                    else:
                        post_data = dict(post)
                    
                    # Add metadata
                    post_data['collected_at'] = datetime.utcnow().isoformat()
                    post_data['platform'] = platform
                    
                    # Save to database
                    if self.db.add_post(post_data):
                        stats['collected'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    print(f"Error processing {platform} post: {e}")
            
            return stats
            
        except Exception as e:
            return {'error': f'Error collecting from {platform}: {str(e)}'}
    
    async def collect_all(self) -> Dict[str, Dict[str, int]]:
        """Collect posts from all platforms"""
        results = {}
        
        for platform in self.extractors.keys():
            results[platform] = await self.collect_from_platform(platform)
            # Add a small delay between platform collections
            await asyncio.sleep(2)
        
        return results
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about the last collection"""
        return self.collection_stats


def run_twitter_collection():
    """Run Twitter collection and return results"""
    service = CollectionService()
    return asyncio.run(service.collect_from_platform('twitter'))

def run_reddit_collection():
    """Run Reddit collection and return results"""
    service = CollectionService()
    return asyncio.run(service.collect_from_platform('reddit'))

def run_threads_collection():
    """Run Threads collection and return results"""
    # Placeholder for Threads collection
    return {'error': 'Threads collection not yet implemented'}
