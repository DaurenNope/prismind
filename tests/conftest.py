"""
Pytest configuration and shared fixtures.
"""

import pytest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Set test environment variables
os.environ.setdefault('TESTING', 'true')
os.environ.setdefault('LOG_LEVEL', 'DEBUG')


@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory"""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def sample_post():
    """Return a sample post for testing - matches real data structure from analysis pipeline"""
    from datetime import datetime, timezone
    
    return {
        # Core post fields
        'post_id': 'test_post_123',
        'platform': 'twitter',
        'content': 'This is a sample post for testing purposes. It has enough content to pass quality checks.',
        'title': 'Test Post Title',
        'url': 'https://twitter.com/test/123',
        'author': 'test_author',
        'author_handle': '@test_author',
        'username': '@test_author',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'hashtags': ['test', 'sample'],
        'engagement': {'likes': 100, 'retweets': 50},
        'media_urls': [],
        'post_type': 'text',
        
        # Required analysis fields (from analysis pipeline)
        'ai_summary': 'This is a sample AI summary for testing purposes. It has enough content to pass quality checks.',
        'category': 'Technology',
        'value_score': 7.0,
        'quality_score': 7.0,
        'key_concepts': ['testing', 'sample', 'quality'],
        'topics': ['Testing', 'Quality Assurance'],
        'tags': ['test', 'sample', 'qa'],
        
        # Optional analysis fields
        'subcategory': 'Testing',
        'content_type': 'Tutorial',
        'sentiment': 'Positive',
        'rewrite_score': 7.0,
        'relevance_window': 'evergreen',
        'urgency_score': 0.2,
        'time_sensitive': False,
        'best_persona_key': 'qronoya',
        'best_persona_score': 7.0,
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
        'analysis_model': 'ollama',
        'analysis_version': '1.0',
    }


@pytest.fixture(scope="session")
def sample_truncated_post():
    """Return a sample truncated post for testing - matches real data structure"""
    from datetime import datetime, timezone
    
    return {
        # Core post fields
        'post_id': 'test_post_truncated',
        'platform': 'twitter',
        'content': 'This is truncated content that ends with...',
        'url': 'https://twitter.com/test/truncated',
        'author': 'test_author',
        'created_at': datetime.now(timezone.utc).isoformat(),
        
        # Required analysis fields (may be empty for truncated posts)
        'ai_summary': 'This is a summary',
        'category': 'General',
        'value_score': 5.0,
        'quality_score': 5.0,
        'key_concepts': [],
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture(scope="session")
def sample_error_post():
    """Return a sample error post for testing - matches real data structure"""
    from datetime import datetime, timezone
    
    return {
        # Core post fields
        'post_id': 'test_post_error',
        'platform': 'twitter',
        'content': 'JavaScript is not available. Please enable JavaScript to continue.',
        'url': 'https://twitter.com/test/error',
        'author': 'test_author',
        'created_at': datetime.now(timezone.utc).isoformat(),
        
        # Required analysis fields (may be empty for error posts)
        'ai_summary': 'This is a summary',
        'category': 'General',
        'value_score': 0.0,
        'quality_score': 0.0,
        'key_concepts': [],
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment before each test"""
    # Store original environment
    original_env = os.environ.copy()
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================================
# Persona Config Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def sample_persona_config():
    """Return a sample persona configuration"""
    return {
        "key": "test_persona",
        "name": "Test Persona",
        "language": "english",
        "tone": "professional",
        "platforms": ["twitter", "threads"],
        "expertise": ["Technology", "Startups"],
        "voice_description": "Tech professional writing about technology and startups",
        "filters": {
            "keywords": ["tech", "startup", "technology"],
            "min_length": 40,
            "max_length": 1200
        },
        "quality_thresholds": {
            "min_value_score": 4.5,
            "min_content_quality": 3.0
        }
    }


@pytest.fixture(scope="session")
def qronoya_persona_config():
    """Return Qronoya persona configuration"""
    return {
        "key": "qronoya",
        "name": "Qronoya",
        "language": "russian",
        "tone": "professional",
        "platforms": ["twitter", "threads", "telegram"],
        "expertise": ["Technology", "Startups", "Entrepreneurship"],
        "voice_description": "Tech professional and entrepreneur"
    }


# ============================================================================
# Example Post Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def example_post_tech():
    """Return an example tech post"""
    from datetime import datetime, timezone
    
    return {
        "id": 1,
        "platform": "twitter",
        "content": "Python is revolutionizing data science with powerful libraries like pandas and numpy. The ecosystem continues to grow.",
        "notes": "Good example of tech content",
        "why_good_example": "Shows technical vocabulary and professional tone"
    }


@pytest.fixture(scope="session")
def example_post_startup():
    """Return an example startup post"""
    from datetime import datetime, timezone
    
    return {
        "id": 2,
        "platform": "twitter",
        "content": "Building a startup requires focus, determination, and the right tools. Start small, iterate fast.",
        "notes": "Good example of startup content",
        "why_good_example": "Shows practical advice and action-oriented tone"
    }


@pytest.fixture(scope="session")
def example_posts_list():
    """Return a list of example posts"""
    return [
        {
            "id": 1,
            "platform": "twitter",
            "content": "Python is great for data science",
            "notes": "Tech example"
        },
        {
            "id": 2,
            "platform": "threads",
            "content": "Building startups requires focus",
            "notes": "Startup example"
        },
        {
            "id": 3,
            "platform": "twitter",
            "content": "Learning programming step by step",
            "notes": "Educational example"
        }
    ]


# ============================================================================
# Mock RAG System Fixtures
# ============================================================================

@pytest.fixture
def mock_rag_system():
    """Return a mock RAG system"""
    mock_rag = Mock()
    mock_rag.search_similar = Mock(return_value=[
        {
            "content": "Example content 1",
            "score": 0.85,
            "metadata": {"platform": "twitter", "source": "rag"}
        },
        {
            "content": "Example content 2",
            "score": 0.80,
            "metadata": {"platform": "threads", "source": "rag"}
        }
    ])
    mock_rag.add_example = Mock(return_value="example_id_123")
    mock_rag.add_examples_batch = Mock(return_value=["id1", "id2", "id3"])
    return mock_rag


@pytest.fixture
def mock_rag_system_disabled():
    """Return a mock RAG system that is disabled"""
    mock_rag = Mock()
    mock_rag.search_similar = Mock(return_value=[])
    mock_rag.add_example = Mock(return_value=None)
    mock_rag.model = None  # Simulate disabled model
    return mock_rag


@pytest.fixture
def mock_rag_system_error():
    """Return a mock RAG system that raises errors"""
    mock_rag = Mock()
    mock_rag.search_similar = Mock(side_effect=Exception("RAG system error"))
    mock_rag.add_example = Mock(side_effect=Exception("RAG system error"))
    return mock_rag


# ============================================================================
# Mock AI Service Fixtures
# ============================================================================

@pytest.fixture
def mock_ai_service():
    """Return a mock AI service"""
    mock_ai = Mock()
    mock_ai.generate_text = Mock(return_value="Generated text from AI service")
    mock_ai.analyze_content = Mock(return_value={
        "category": "TECH",
        "key_concepts": ["Python", "programming"],
        "topics": ["technology"],
        "value_score": 7.5,
        "quality_score": 8.0
    })
    mock_ai.rewrite_content = Mock(return_value="Rewritten content")
    return mock_ai


@pytest.fixture
def mock_ai_service_error():
    """Return a mock AI service that raises errors"""
    mock_ai = Mock()
    mock_ai.generate_text = Mock(side_effect=Exception("AI service error"))
    mock_ai.analyze_content = Mock(side_effect=Exception("AI service error"))
    mock_ai.rewrite_content = Mock(side_effect=Exception("AI service error"))
    return mock_ai


@pytest.fixture
def mock_ollama_service():
    """Return a mock Ollama service"""
    mock_ollama = Mock()
    mock_ollama.generate = Mock(return_value="Ollama generated text")
    mock_ollama.is_available = Mock(return_value=True)
    return mock_ollama


@pytest.fixture
def mock_gemini_service():
    """Return a mock Gemini service"""
    mock_gemini = Mock()
    mock_gemini.generate = Mock(return_value="Gemini generated text")
    mock_gemini.is_available = Mock(return_value=True)
    return mock_gemini


# ============================================================================
# Voice Fragment Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def sample_voice_fragments():
    """Return sample voice fragments"""
    return [
        {
            "text": "Python is a powerful tool",
            "context": "Technical discussion",
            "score": 0.9
        },
        {
            "text": "Building startups requires focus",
            "context": "Entrepreneurship advice",
            "score": 0.85
        },
        {
            "text": "Learning step by step",
            "context": "Educational content",
            "score": 0.80
        }
    ]


# ============================================================================
# Analyzed Content Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def sample_analyzed_content():
    """Return sample analyzed content"""
    from datetime import datetime, timezone
    
    return {
        'post_id': 'analyzed_test_123',
        'platform': 'twitter',
        'content': 'Python is revolutionizing data science with powerful libraries.',
        'title': 'Python for Data Science',
        'url': 'https://twitter.com/test/123',
        'author': 'test_author',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'ai_summary': 'Python programming language for data science',
        'category': 'TECH',
        'key_concepts': ['Python', 'data science', 'libraries'],
        'topics': ['programming', 'data analysis'],
        'value_score': 8.0,
        'quality_score': 8.5,
        'rewrite_score': 7.5,
        'complexity': 'Intermediate',
        'rewrite_angles': [
            {
                'persona': 'technical',
                'angle': 'Deep dive into Python data science libraries',
                'hook': 'Python libraries are game-changers',
                'key_points': ['pandas', 'numpy', 'scikit-learn'],
                'estimated_engagement': 'high'
            }
        ]
    }


@pytest.fixture(scope="session")
def sample_rewrite_angle():
    """Return a sample rewrite angle"""
    return {
        'persona': 'technical',
        'angle': 'Deep technical analysis of Python data science ecosystem',
        'hook': 'Python libraries are revolutionizing data science workflows',
        'key_points': [
            'pandas for data manipulation',
            'numpy for numerical computing',
            'scikit-learn for machine learning'
        ],
        'target_audience': 'Data scientists and developers',
        'estimated_engagement': 'high'
    }


# ============================================================================
# Mock Database Fixtures
# ============================================================================

@pytest.fixture
def mock_database():
    """Return a mock database manager"""
    mock_db = Mock()
    mock_db.get_post = Mock(return_value=None)
    mock_db.get_posts = Mock(return_value=[])
    mock_db.get_unanalyzed_posts = Mock(return_value=[])
    mock_db.save_post = Mock(return_value=True)
    mock_db.update_post = Mock(return_value=True)
    mock_db.get_posts_by_platform = Mock(return_value=[])
    return mock_db


@pytest.fixture
def mock_supabase_client():
    """Return a mock Supabase client"""
    mock_client = Mock()
    mock_table = Mock()
    mock_table.select.return_value.execute.return_value.data = []
    mock_table.insert.return_value.execute.return_value.data = [{'id': 1}]
    mock_table.update.return_value.execute.return_value.data = [{'id': 1}]
    mock_client.table.return_value = mock_table
    return mock_client


@pytest.fixture
def mock_storage_facade():
    """Return a mock storage facade"""
    from unittest.mock import Mock, patch
    
    with patch('src.storage.db.get_config') as mock_config:
        mock_config.return_value.flags = {
            'supabase_enabled': True,
            'enable_sqlite_cache': True,
        }
        
        from src.infrastructure.database.storage.db import StorageFacade
        storage = StorageFacade()
        
        # Mock Supabase
        mock_supabase = Mock()
        mock_supabase.save_post = Mock(return_value=True)
        mock_supabase.get_post = Mock(return_value=None)
        mock_supabase.get_posts = Mock(return_value=[])
        mock_supabase.get_unanalyzed_posts = Mock(return_value=[])
        storage._supabase = mock_supabase
        
        # Mock SQLite if present
        if storage._sqlite:
            storage._sqlite.save_post = Mock(return_value=True)
            storage._sqlite.get_post = Mock(return_value=None)
            storage._sqlite.get_posts = Mock(return_value=[])
        
        return storage


# ============================================================================
# Analysis Result Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def complete_analysis_result():
    """Complete analysis result with all required and optional fields"""
    from datetime import datetime, timezone
    
    return {
        # Core identification
        'post_id': 'test_post_123',
        'platform': 'twitter',
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
        'analysis_version': '1.0',
        
        # Required fields
        'ai_summary': 'This is a comprehensive AI summary of the post content',
        'category': 'Technology',
        'value_score': 8.5,
        'quality_score': 8.0,
        'key_concepts': ['Python', 'Data Science', 'Machine Learning'],
        
        # Optional but recommended fields
        'subcategory': 'Data Science',
        'content_type': 'Tutorial',
        'topics': ['Python', 'Data Science', 'Programming'],
        'tags': ['python', 'datascience', 'programming'],
        'sentiment': 'Positive',
        'sentiment_scores': {'pos': 0.8, 'neu': 0.2, 'neg': 0.0},
        'complexity_level': 'Intermediate',
        'time_to_consume': '5 minutes',
        'actionable_items': ['Learn Python', 'Try pandas'],
        'practical_applications': ['Data analysis', 'Machine learning'],
        'confidence_score': 0.9,
        'ai_service': 'gemini',
    }


@pytest.fixture(scope="session")
def minimal_analysis_result():
    """Minimal analysis result with only required fields"""
    from datetime import datetime, timezone
    
    return {
        'ai_summary': 'Python for data science',
        'category': 'Technology',
        'value_score': 7.0,
        'quality_score': 7.0,
        'key_concepts': ['Python'],
    }


@pytest.fixture(scope="session")
def empty_analysis_result():
    """Analysis result with empty/missing fields (for testing fallbacks)"""
    from datetime import datetime, timezone
    
    return {
        'post_id': 'test_post_123',
        'platform': 'twitter',
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture(scope="session")
def partial_analysis_result():
    """Partial analysis result with some fields missing"""
    from datetime import datetime, timezone
    
    return {
        'post_id': 'test_post_123',
        'platform': 'twitter',
        'analyzed_at': datetime.now(timezone.utc).isoformat(),
        'ai_summary': 'Test summary',
        'category': 'Technology',
        # value_score missing
        'quality_score': 7.0,
        'key_concepts': ['Python'],
    }


# ============================================================================
# Mock API Response Fixtures
# ============================================================================

@pytest.fixture
def mock_api_response_success():
    """Return a mock successful API response"""
    return {
        'status': 'success',
        'data': {},
        'message': 'Operation completed successfully'
    }


@pytest.fixture
def mock_api_response_error():
    """Return a mock error API response"""
    return {
        'status': 'error',
        'error': 'Operation failed',
        'error_code': 'E001'
    }


@pytest.fixture
def mock_dashboard_stats_response():
    """Return mock dashboard stats response"""
    return {
        'total_posts': 100,
        'platforms': {
            'twitter': 50,
            'reddit': 30,
            'threads': 20
        },
        'analyzed': 80,
        'unanalyzed': 20,
        'last_automation_run': datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def mock_collection_status_response():
    """Return mock collection status response"""
    return {
        'collectors': [
            {
                'platform': 'twitter',
                'status': 'idle',
                'last_run': datetime.now(timezone.utc).isoformat(),
                'posts_collected': 10
            }
        ]
    }


# ============================================================================
# Test Data Generators
# ============================================================================

@pytest.fixture
def generate_test_posts():
    """Generator function for test posts"""
    def _generate(count: int = 10, platform: str = 'twitter', analyzed: bool = False):
        posts = []
        for i in range(count):
            post = {
                'post_id': f'test_post_{platform}_{i}',
                'platform': platform,
                'content': f'Test content {i} for {platform}',
                'title': f'Test Title {i}',
                'url': f'https://{platform}.com/test/{i}',
                'author': f'test_author_{i}',
                'author_handle': f'@test_author_{i}',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'collected_at': datetime.now(timezone.utc).isoformat(),
            }
            if analyzed:
                post['analyzed_at'] = datetime.now(timezone.utc).isoformat()
                # Required analysis fields
                post['ai_summary'] = f'AI summary for post {i}'
                post['category'] = 'Technology'
                post['value_score'] = 7.0
                post['quality_score'] = 7.5
                post['key_concepts'] = ['concept1', 'concept2']
                post['topics'] = ['Topic 1', 'Topic 2']
                post['tags'] = ['tag1', 'tag2']
            posts.append(post)
        return posts
    return _generate


@pytest.fixture
def generate_test_personas():
    """Generator function for test personas"""
    def _generate(count: int = 3):
        personas = []
        persona_names = ['qronoya', 'aspandead', 'claimzilla']
        for i, name in enumerate(persona_names[:count]):
            persona = {
                'key': name,
                'name': name.capitalize(),
                'language': 'english' if i > 0 else 'russian',
                'tone': 'professional',
                'platforms': ['twitter', 'threads'],
                'expertise': ['Technology', 'Startups']
            }
            personas.append(persona)
        return personas
    return _generate


@pytest.fixture
def generate_test_rewrite_angles():
    """Generator function for test rewrite angles"""
    def _generate(persona: str = 'technical'):
        return [
            {
                'persona': persona,
                'angle': f'Deep analysis for {persona} persona',
                'hook': f'Compelling hook for {persona}',
                'key_points': ['Point 1', 'Point 2', 'Point 3'],
                'estimated_engagement': 'high'
            }
        ]
    return _generate
