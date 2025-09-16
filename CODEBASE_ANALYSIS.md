# Prismind Codebase Analysis

## Core Extraction Module

### Base Classes

#### `social_extractor_base.py`
- **Purpose**: Defines the base class and data model for all social media extractors
- **Key Components**:
  - `SocialPost` dataclass: Standardized format for social media posts
  - `SocialExtractorBase` abstract base class with required methods
- **Key Methods**:
  - `authenticate()`: Abstract method for platform authentication
  - `get_saved_posts()`: Abstract method to fetch saved/bookmarked posts
  - `get_liked_posts()`: Abstract method to fetch liked posts
  - `validate_credentials()`: Validates authentication
  - `format_post_for_analysis()`: Prepares post data for AI processing

### Implementations

#### `reddit_extractor.py`
- **Purpose**: Implements Reddit-specific data extraction
- **Key Features**:
  - Handles both OAuth and username/password authentication
  - Implements connection pooling and retry logic
  - Custom DNS resolution for Reddit domains
  - Comprehensive error handling
- **Dependencies**:
  - `praw`: Python Reddit API Wrapper
  - `requests`: HTTP client
  - `urllib3`: HTTP client utilities

#### `twitter_extractor_playwright.py`
- **Purpose**: Extracts data from Twitter using Playwright
- **Key Features**:
  - Browser automation for Twitter data extraction
  - Cookie-based session management
  - Handles Twitter's dynamic content loading
- **Dependencies**:
  - `playwright`: Browser automation
  - `asyncio`: Asynchronous operations

#### Other Extractors
- `instagram_extractor.py`: Placeholder for Instagram integration
- `threads_extractor.py`: Placeholder for Threads integration

## Core Analysis Module

### `content_analyzer.py`
- **Purpose**: Provides AI-powered content analysis
- **Key Features**:
  - Integration with local Ollama models
  - Standardized analysis format
  - Fallback mechanisms for analysis failures
- **Dependencies**:
  - `requests`: For API calls to Ollama

### `intelligent_content_analyzer.py`
- **Purpose**: Advanced content analysis with multiple AI providers
- **Key Features**:
  - Support for multiple AI backends
  - Content summarization and classification
  - Sentiment analysis

### `local_media_analyzer.py`
- **Purpose**: Analyzes locally stored media files
- **Key Features**:
  - Image and video analysis
  - Metadata extraction
  - Content classification

### `media_analyzer.py`
- **Purpose**: Base class for media analysis
- **Key Features**:
  - Common interface for media processing
  - Support for different media types
  - Extensible architecture

### `mistral_analyzer.py`
- **Purpose**: Integration with Mistral AI models
- **Key Features**:
  - Text analysis using Mistral
  - Custom model configurations
  - Batch processing support

### `shuttleai_analyzer.py`
- **Purpose**: Integration with ShuttleAI API
- **Key Features**:
  - Cloud-based AI analysis
  - High-volume processing
  - API key management

### `social_content_analyzer.py`
- **Purpose**: Specialized analysis for social media content
- **Key Features**:
  - Platform-specific content processing
  - Engagement metrics analysis
  - Trend detection

### `thread_summarizer.py`
- **Purpose**: Summarizes conversation threads
- **Key Features**:
  - Thread reconstruction
  - Key point extraction
  - Context-aware summarization

### `value_scorer.py`
- **Purpose**: Assigns value scores to content
- **Key Features**:
  - Custom scoring algorithms
  - Relevance ranking
  - Personalization features

## Core Collection Module

### `unified_collector.py`
- **Purpose**: Coordinates multiple extractors and analyzers
- **Key Features**:
  - Unified interface for all platforms
  - Automatic extractor initialization based on environment variables
  - Asynchronous processing of content
  - Standardized output format
  - Error handling and logging
- **Methods**:
  - `__init__`: Initializes the collector with configuration
  - `_initialize_extractors`: Sets up platform-specific extractors
  - `collect_saved_content`: Main method to collect and analyze content
  - `collect_and_analyze_all`: Collects from all configured platforms
- **Dependencies**:
  - `reddit_extractor`: For Reddit content
  - `twitter_extractor_playwright`: For Twitter content
  - `content_analyzer`: For AI-powered analysis
- **Configuration**:
  - Uses environment variables for credentials
  - Supports both Reddit and Twitter
  - Configurable limits for content collection

## Services

### Core Services

#### `analyzer.py`
- **Purpose**: Main analysis service
- **Key Features**:
  - Coordinates content analysis
  - Manages analysis pipelines
  - Handles analysis results

#### `collection_service.py`
- **Purpose**: Manages content collection
- **Key Features**:
  - Coordinates extractors
  - Handles collection scheduling
  - Manages collection state

#### `collector.py`
- **Purpose**: Base collector implementation
- **Key Features**:
  - Defines collector interface
  - Handles common collection tasks
  - Provides base functionality

### Scheduling

#### `scheduler.py`
- **Purpose**: Job scheduling
- **Key Features**:
  - Manages scheduled tasks
  - Handles job execution
  - Provides scheduling utilities

#### `aps_scheduler_runner.py`
- **Purpose**: APScheduler integration
- **Key Features**:
  - Background job scheduling
  - Job persistence
  - Event handling

### Notification

#### `notifier.py`
- **Purpose**: Notification service
- **Key Features**:
  - Sends notifications
  - Supports multiple backends
  - Handles notification templates

#### `notifier_webhook.py`
- **Purpose**: Webhook notifications
- **Key Features**:
  - Sends webhook events
  - Handles webhook configuration
  - Manages retries and errors

### Data Management

#### `database.py`
- **Purpose**: Database connection management
- **Key Features**:
  - Handles database connections
  - Manages connection pooling
  - Provides query utilities

#### `database_manager.py`
- **Purpose**: High-level database operations
- **Key Features**:
  - Schema management
  - Data migration
  - Backup/restore

### Integration

#### `supabase_webhook.py`
- **Purpose**: Supabase webhook integration
- **Key Features**:
  - Handles Supabase events
  - Processes database changes
  - Triggers workflows

#### `telegram_bot.py`
- **Purpose**: Telegram bot integration
- **Key Features**:
  - Handles Telegram commands
  - Sends notifications
  - Manages bot state

### Configuration

#### `preferences.py`
- **Purpose**: User preferences
- **Key Features**:
  - Manages user settings
  - Handles preference storage
  - Provides defaults

### Runners

#### `collector_runner.py`
- **Purpose**: Runs collection jobs
- **Key Features**:
  - Manages collection execution
  - Handles errors and retries
  - Logs collection metrics

#### `collector_runner_clean.py`
- **Purpose**: Clean version of collector runner
- **Key Features**:
  - Simplified execution
  - Minimal dependencies
  - Easy to debug

## Web Interface

### Core Application (`app.py`)
- **Purpose**: Main Streamlit application
- **Key Features**:
  - Streamlit-based web interface
  - Multi-tab layout (Dashboard, Analytics, Settings)
  - Background collection automation
  - Real-time updates
- **Components**:
  - Session state management
  - Background task handling
  - Database integration
  - Collection automation controls

### Dashboard Components (`/src/web/components/`)

#### `dashboard.py`
- **Purpose**: Main dashboard view
- **Features**:
  - Tabbed interface (Posts, Analytics, Settings)
  - Post filtering and search
  - Pagination
  - Interactive cards for posts
- **Key Functions**:
  - `render_dashboard()`: Main dashboard layout
  - `render_posts_tab()`: Displays and filters posts
  - `render_analytics_tab()`: Shows analytics and insights
  - `render_settings_tab()`: Application settings

#### `sidebar.py`
- **Purpose**: Navigation and status sidebar
- **Features**:
  - System status indicators
  - Collection controls
  - Quick actions
  - User preferences

### Database Integration
- **Supported Backends**:
  - Supabase (cloud)
  - SQLite (local)
  - In-memory (demo)
- **Features**:
  - Automatic connection management
  - Caching layer
  - Error handling

### Collection Services
- **Platforms Supported**:
  - Twitter
  - Reddit
  - Threads (in development)
- **Features**:
  - Scheduled collection
  - Background processing
  - Progress tracking
  - Error handling and retries

## Test Coverage

### Test Structure

#### Unit Tests (`/tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Key Test Files**:
  - `test_duplicate_detection.py`: Tests for duplicate content detection
  - `test_notification.py`: Notification service tests
  - `test_reddit_connectivity.py`: Reddit API connectivity tests
  - `test_telegram.py`: Telegram bot functionality tests

#### Integration Tests (`/tests/integration/`)
- **Purpose**: Test interactions between components
- **Key Test Files**:
  - `test_supabase_integration.py`: Database integration tests
  - `test_webhook_notifier.py`: Webhook notification tests
  - `test_social_content_analyzer.py`: Content analysis integration

#### End-to-End Tests (`/tests/e2e/`)
- **Purpose**: Test complete workflows
- **Key Test Files**:
  - `test_pipeline.py`: Full collection and analysis pipeline

#### Current Functionality Tests (`/tests/current_functionality/`)
- **Purpose**: Test core application workflows
- **Key Test Files**:
  - `test_dashboard_workflow.py`: Dashboard UI and functionality
  - `test_data_collection.py`: Data collection processes

### Test Categories

#### Core Functionality
- Database operations
- Authentication flows
- Data collection
- Content analysis

#### Integration Points
- Social media APIs
- External services (Supabase, Telegram)
- Notification systems

#### Performance
- Collection speed
- Analysis performance
- Database query optimization

### Test Coverage Gaps
1. **Missing Tests**:
   - Some analysis components lack comprehensive tests
   - Limited browser automation tests
   - Sparse error handling tests

2. **Areas Needing Improvement**:
   - Mock external services more thoroughly
   - Add more edge case testing
   - Increase test data variety

3. **Test Data**:
   - Need more diverse test data
   - Add performance test scenarios
   - Include stress testing

### Testing Dependencies
- `pytest`: Test framework
- `pytest-mock`: Mocking library
- `pytest-cov`: Coverage reporting
- `pytest-asyncio`: Async test support
- `responses`: HTTP request mocking

## Configuration

### Environment Variables

#### `.env` File
- **Purpose**: Stores sensitive configuration and API keys
- **Location**: Project root (not versioned)
- **Required Variables**:
  ```
  # Reddit API
  REDDIT_CLIENT_ID=your_client_id_here
  REDDIT_CLIENT_SECRET=your_client_secret_here
  REDDIT_USERNAME=your_reddit_username
  REDDIT_PASSWORD=your_reddit_password
  
  # OpenAI API
  OPENAI_API_KEY=your_openai_api_key_here
  
  # Telegram
  TELEGRAM_BOT_TOKEN=your_telegram_bot_token
  TELEGRAM_CHAT_ID=your_telegram_chat_id
  
  # Twitter API (future use)
  TWITTER_API_KEY=your_twitter_api_key
  TWITTER_API_SECRET=your_twitter_api_secret
  ```

#### `.env.example`
- **Purpose**: Template for required environment variables
- **Location**: Project root
- **Usage**: Copy to `.env` and fill in values

### Project Configuration

#### `pyproject.toml`
- **Purpose**: Project metadata and tool configurations
- **Key Sections**:
  - `[tool.ruff]`: Linting configuration
    - Python target version: 3.9
    - Line length: 100 characters
    - Excluded paths (legacy/experimental)
  - `[tool.ruff.lint]`: Linting rules
    - Base rule sets (E, F, I)
    - Ignored rules for legacy code
  - `[tool.ruff.lint.per-file-ignores]`: File-specific rule exceptions

### Deployment Configurations

#### Railway Configuration (`/config/railway.toml`)
- **Purpose**: Railway.app deployment configuration
- **Key Settings**:
  - Build commands
  - Environment variables
  - Health check endpoints

#### Streamlit Secrets (`/config/streamlit_secrets.toml`)
- **Purpose**: Secure storage for Streamlit cloud deployment
- **Content**:
  - Database credentials
  - API keys
  - Other sensitive configuration

### Configuration Management

#### Environment Handling
- **Development**: Uses `.env` file (not versioned)
- **Production**: Uses environment variables in deployment platform
- **Secrets**: Managed through platform-specific secret management

#### Configuration Loading
- Uses `python-dotenv` for local development
- Environment variables take precedence over `.env` file
- Sensitive values are never hardcoded in the codebase

## Scripts

### Core Collection Scripts

#### `run_collector.py`
- **Purpose**: Main script for collecting and analyzing social media content
- **Features**:
  - Collects saved posts from Reddit and Twitter
  - Analyzes content using OpenAI's API
  - Generates summary reports
  - Supports logging and error handling

#### `trigger_collections.py`
- **Purpose**: Manually trigger collection from multiple platforms
- **Features**:
  - Runs both Twitter and Reddit collections
  - Handles duplicate detection
  - Updates database with new posts
  - Provides summary statistics

### Utility Scripts

#### Data Management
- `cleanup_files.py`: Clean up temporary and log files
- `cleanup_root.py`: Clean up root directory
- `organize_root.py`: Organize files in the root directory
- `update_deps.py`: Update project dependencies

#### Testing and Development
- `test_bookmark_collection.py`: Test bookmark collection functionality
- `test_imports.py`: Verify all imports work correctly
- `test_reddit_*.py`: Various Reddit-related test scripts
- `update_imports.py`: Update import statements across the codebase

#### Database Management
- `database_manager.py`: Database management utilities
- `supabase_manager.py`: Supabase integration utilities

### Analysis Scripts
- `fix_categorization.py`: Fix content categorization
- `test_reddit_with_ai.py`: Test Reddit content analysis with AI

### Automation Scripts
- `scheduled_reddit_collector.py`: Scheduled Reddit collection
- `cookie_collectors.py`: Manage browser cookies for authentication
- `export_cookies.py`: Export browser cookies for authentication

### Script Usage

#### Running Collections
```bash
# Run the main collector
python scripts/run_collector.py

# Trigger manual collections
python scripts/trigger_collections.py
```

#### Database Operations
```bash
# Initialize/update database
python scripts/database_manager.py

# Clean up files
python scripts/cleanup_files.py
```

### Script Dependencies
- Core: `requests`, `python-dotenv`, `pandas`
- Database: `sqlite3`, `supabase`
- Testing: `pytest`, `pytest-mock`
- Utilities: `python-dateutil`, `tqdm`

## Identified Issues and TODOs

1. **Redundant Code**:
   - `working_reddit_extractor.py` has been removed (duplicate of `reddit_extractor.py`)

2. **Incomplete Implementations**:
   - Instagram and Threads extractors are stubbed but not fully implemented

3. **Testing Gaps**:
   - Need more comprehensive test coverage
   - Missing tests for some edge cases

4. **Documentation**:
   - Need more detailed API documentation
   - Add usage examples

## Next Steps

1. Complete implementation of missing extractors
2. Enhance test coverage
3. Add comprehensive documentation
4. Implement proper error handling and logging
5. Add monitoring and metrics collection
