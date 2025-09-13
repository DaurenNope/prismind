#!/usr/bin/env python3
"""
Social Media Collector and Analyzer

This script collects saved posts from various social media platforms,
analyzes them using OpenAI's API, and generates a summary report.
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('collection.log')
    ]
)
logger = logging.getLogger(__name__)

class ContentAnalyzer:
    """Handles content analysis using OpenAI's API."""
    
    def __init__(self, openai_api_key):
        self.openai_api_key = openai_api_key
        self.base_url = 'https://api.openai.com/v1/chat/completions'
        
    def analyze_content(self, content_type, content):
        """Analyze content using OpenAI's API."""
        try:
            if content_type == 'reddit':
                prompt = f"""Analyze this Reddit post and provide:
                - Main topic/theme
                - Key points
                - Sentiment (positive/negative/neutral)
                - Potential value/importance (1-10)
                
                Title: {content.get('title', 'No title')}
                Content: {content.get('selftext', 'No content')[:2000]}..."""
            
            elif content_type == 'twitter':
                prompt = f"""Analyze this Tweet and provide:
                - Main topic/theme
                - Key points
                - Sentiment (positive/negative/neutral)
                - Engagement potential (1-10)
                
                Tweet: {content.get('text', 'No content')}"""
            else:
                return {'status': 'error', 'error': 'Unsupported content type'}
            
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'system', 'content': 'You are a helpful assistant that analyzes social media content.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7
            }
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            analysis = response.json()['choices'][0]['message']['content']
            return {'status': 'success', 'analysis': analysis}
            
        except Exception as e:
            logger.error(f'Analysis failed: {str(e)}')
            return {'status': 'error', 'error': str(e)}

class Collector:
    """Main collector class that handles the collection and analysis pipeline."""
    
    def __init__(self):
        self.results = {}
        self.analyzer = ContentAnalyzer(os.getenv('OPENAI_API_KEY', ''))
        self.start_time = datetime.utcnow()
        
    def collect_reddit(self):
        """Collect and analyze Reddit saved posts."""
        try:
            from src.core.extraction.working_reddit_extractor import WorkingRedditExtractor
            logger.info('🔴 Starting Reddit collection...')
            
            extractor = WorkingRedditExtractor()
            posts = extractor.get_saved_posts(limit=10)
            
            analyzed_posts = []
            for post in posts:
                post_data = {
                    'title': post.get('title'),
                    'url': post.get('url'),
                    'created': post.get('created_timestamp'),
                    'subreddit': post.get('subreddit'),
                    'author': post.get('author')
                }
                
                analysis = self.analyzer.analyze_content('reddit', post)
                post_data['analysis'] = analysis
                analyzed_posts.append(post_data)
            
            self.results['reddit'] = {
                'status': 'success',
                'count': len(analyzed_posts),
                'posts': analyzed_posts
            }
            logger.info(f'✅ Collected and analyzed {len(analyzed_posts)} Reddit posts')
            
        except Exception as e:
            logger.error(f'❌ Reddit collection failed: {str(e)}')
            self.results['reddit'] = {'status': 'error', 'error': str(e)}
    
    def collect_twitter(self):
        """Collect and analyze Twitter saved posts (stub for now)."""
        try:
            from src.core.extraction.twitter_extractor import TwitterExtractor
            logger.info('🐦 Starting Twitter collection...')
            
            # Initialize Twitter extractor
            extractor = TwitterExtractor()
            
            # Get saved tweets (implementation needed)
            tweets = []  # extractor.get_saved_tweets(limit=10)
            
            analyzed_tweets = []
            for tweet in tweets:
                tweet_data = {
                    'text': tweet.get('text'),
                    'url': tweet.get('url'),
                    'created': tweet.get('created_at'),
                    'author': tweet.get('author')
                }
                
                analysis = self.analyzer.analyze_content('twitter', tweet)
                tweet_data['analysis'] = analysis
                analyzed_tweets.append(tweet_data)
            
            self.results['twitter'] = {
                'status': 'success' if tweets else 'not_implemented',
                'count': len(analyzed_tweets),
                'tweets': analyzed_tweets
            }
            logger.info(f'✅ Collected and analyzed {len(analyzed_tweets)} Tweets')
            
        except Exception as e:
            logger.error(f'❌ Twitter collection failed: {str(e)}')
            self.results['twitter'] = {'status': 'error', 'error': str(e)}
    
    def generate_telegram_message(self):
        """Generate a formatted message for Telegram."""
        message = ["🌐 *Social Media Collection Complete*\n"]
        
        # Add Reddit section
        if 'reddit' in self.results and self.results['reddit']['status'] == 'success':
            reddit = self.results['reddit']
            message.append(f"🔴 *Reddit*: {reddit['count']} posts collected")
            
            for i, post in enumerate(reddit['posts'][:3], 1):  # Show top 3
                message.append(f"\n*{i}. {post['title']}*")
                message.append(f"   r/{post.get('subreddit', 'unknown')} • {post.get('url', '')}")
                
                # Add analysis summary if available
                if 'analysis' in post and post['analysis']['status'] == 'success':
                    analysis = post['analysis']['analysis'].split('\n')[0]  # Just first line
                    message.append(f"   _{analysis}_")
            
            if reddit['count'] > 3:
                message.append(f"\n... and {reddit['count'] - 3} more posts")
        
        # Add Twitter section
        if 'twitter' in self.results:
            if self.results['twitter']['status'] == 'success':
                tw = self.results['twitter']
                message.append(f"\n🐦 *Twitter*: {tw['count']} tweets collected")
                # Add tweet previews when implemented
            elif self.results['twitter']['status'] == 'not_implemented':
                message.append("\n⚠️ *Twitter*: Collection not implemented yet")
            else:
                message.append("\n❌ *Twitter*: Collection failed")
        
        # Add duration
        duration = (datetime.utcnow() - self.start_time).total_seconds() / 60
        message.append(f"\n⏱️ Completed in {duration:.1f} minutes")
        
        # Add link to run details
        run_url = f"{os.getenv('GITHUB_SERVER_URL', '')}/{os.getenv('GITHUB_REPOSITORY', '')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}"
        message.append(f"\n[View Run Details]({run_url})")
        
        return '\n'.join(message)
    
    def run(self):
        """Run the collection and analysis pipeline."""
        logger.info("🚀 Starting social media collection and analysis...")
        
        # Run all collectors
        self.collect_reddit()
        self.collect_twitter()
        
        # Generate results
        self.results['duration_seconds'] = (datetime.utcnow() - self.start_time).total_seconds()
        self.results['end_time'] = datetime.utcnow().isoformat()
        
        # Generate Telegram message
        telegram_message = self.generate_telegram_message()
        
        # Save results
        with open('collection_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Set output for GitHub Actions
        print(f'::set-output name=telegram_message::{telegram_message}')
        
        logger.info("✅ Collection and analysis completed")
        return self.results

if __name__ == '__main__':
    collector = Collector()
    results = collector.run()
