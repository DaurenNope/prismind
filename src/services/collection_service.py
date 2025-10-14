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
from src.core.extraction.threads_extractor import ThreadsExtractor
from src.pipeline.orchestrator import get_orchestrator

# Load environment variables
load_dotenv()

class CollectionService:
    """Service for managing post collection from various platforms (delegates to orchestrator)."""
    
    def __init__(self):
        self.orch = get_orchestrator()
        self.extractors = {
            'twitter': TwitterExtractorPlaywright,
            'reddit': RedditExtractor,
            'threads': ThreadsExtractor
        }
        self.collection_stats = {}
    
    async def collect_from_platform(self, platform: str) -> Dict[str, int]:
        """Collect posts from a specific platform"""
        if platform not in self.extractors:
            return {'error': f'Unsupported platform: {platform}'}
        
        try:
            count = await self.orch.collect_platform(platform)
            return {'collected': count, 'status': 'success'}
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
    """Run Threads collection using the collector runner"""
    service = CollectionService()
    return asyncio.run(service.collect_from_platform('threads'))
