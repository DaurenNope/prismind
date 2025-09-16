#!/usr/bin/env python3
"""
Test script for AI analysis with proper configuration.
"""
import os
import sys
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Set up environment variables for AI services."""
    # Load AI services config
    config_path = project_root / 'config' / 'ai_services.json'
    try:
        with open(config_path) as f:
            config = json.load(f)
            
        # Set up environment variables based on config
        if config.get('ollama', {}).get('enabled'):
            os.environ['OLLAMA_URL'] = config['ollama'].get('url', 'http://localhost:11434')
            logger.info("Ollama service configured")
            
        if config.get('openai', {}).get('enabled'):
            if api_key := os.getenv('OPENAI_API_KEY') or config['openai'].get('api_key'):
                os.environ['OPENAI_API_KEY'] = api_key
                logger.info("OpenAI service configured")
            else:
                logger.warning("OpenAI enabled but no API key found")
                
        if config.get('gemini', {}).get('enabled'):
            if api_key := os.getenv('GEMINI_API_KEY') or config['gemini'].get('api_key'):
                os.environ['GEMINI_API_KEY'] = api_key
                logger.info("Gemini service configured")
            else:
                logger.warning("Gemini enabled but no API key found")
                
    except Exception as e:
        logger.error(f"Error loading AI config: {e}")

def test_analysis():
    """Test the AI analysis with a sample post."""
    from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
    from src.core.extraction.social_extractor_base import SocialPost
    from datetime import datetime
    
    logger.info("Initializing analyzer...")
    analyzer = IntelligentContentAnalyzer()
    
    # Create a sample post
    sample_post = SocialPost(
        platform="reddit",
        author="test_user",
        author_handle="u/test_user",
        content="""
        I've been working on a new AI model that can generate code from natural language descriptions. 
        It's called CodeGen and it's built on top of GPT-3.5. 
        The model can understand programming concepts and generate working code in multiple languages.
        
        Key features:
        - Natural language to code generation
        - Support for 10+ programming languages
        - Context-aware completions
        - Error detection and suggestions
        
        What do you think about this approach? Would you find this useful for your workflow?
        """,
        created_at=datetime.now(),
        url="https://reddit.com/r/MachineLearning/comments/example",
        post_type="post",
        media_urls=[],
        hashtags=["AI", "CodeGeneration", "MachineLearning"],
        mentions=[],
        engagement={"upvotes": 42, "comments": 7, "shares": 3},
        is_saved=True,
        saved_at=datetime.now(),
        folder_category="ai_research",
        id="test123",
        post_id="test123"
    )
    
    logger.info("Analyzing post...")
    analysis = analyzer.analyze_bookmark(post=sample_post, include_comments=False)
    
    print("\n=== Analysis Results ===")
    print(f"Summary: {analysis.get('summary', 'No summary')}")
    print(f"Value Score: {analysis.get('value_score', 'N/A')}")
    print(f"Key Concepts: {', '.join(analysis.get('key_concepts', []))}")
    print(f"Time Sensitive: {analysis.get('is_time_sensitive', False)}")
    print(f"Reason: {analysis.get('time_sensitivity_reason', 'N/A')}")

if __name__ == "__main__":
    setup_environment()
    test_analysis()
