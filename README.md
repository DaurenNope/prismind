## Feature flags

- `SAVE_TO_SUPABASE=1`: push new analyzed posts to Supabase in addition to local SQLite.
- `OLLAMA_URL=http://localhost:11434` and `OLLAMA_MODEL=qwen2.5:7b`: use local Qwen via Ollama as primary analyzer.
- `USE_VALUE_SCORER=0`: disable saving numeric value_score (ranking only).
- `ENABLE_LOCAL_FEEDBACK=0`: disable local feedback learning (kept for legacy tests).

# PrisMind - Intelligent Universal Bookmarker

PrisMind is a powerful personal intelligence engine that transforms your social media bookmarks into a structured, searchable knowledge base. It extracts your saved content from platforms like Twitter, Reddit, and Threads, analyzes it with AI to understand your interests, and organizes it into actionable insights.

## 🚀 Key Features

- **Multi-Platform Extraction**: Pulls saved content from Twitter, Reddit, and Threads
- **AI-Powered Analysis**: Uses Mistral AI, Gemini, and Perplexity to categorize content, assign value scores, and extract insights
- **🖼️ Media Content Analysis**: Analyzes images and videos using local OCR + AI for free, offline processing
- **Interactive Dashboard**: Streamlit-based interface for data exploration and control
- **Comprehensive Testing**: Full test suite covering all core functionality
- **Professional Codebase**: Clean, well-structured code with proper documentation

## 🏗️ Architecture

```
prismind/
├── scripts/
│   ├── dashboard.py              # Streamlit dashboard
│   └── database_manager.py       # Database operations
├── core/
│   ├── analysis/                 # AI analysis modules
│   │   ├── intelligent_content_analyzer.py  # Primary AI analysis
│   │   ├── mistral_analyzer.py             # Mistral AI integration
│   │   ├── shuttleai_analyzer.py           # ShuttleAI integration
│   │   └── value_scorer.py                 # Content value scoring
│   ├── extraction/               # Platform extractors
│   │   ├── twitter_extractor_playwright.py # Twitter extraction
│   │   ├── reddit_extractor.py             # Reddit extraction
│   │   └── threads_extractor.py            # Threads extraction
│   └── learning/                 # Learning and feedback
│       ├── feedback_system.py              # User feedback system
│       └── smart_organizer.py              # Intelligent organization
├── tests/                        # Comprehensive test suite
│   ├── current_functionality/    # Core functionality tests
│   └── test_core_workflow.py    # Workflow integration tests
├── config/                       # Configuration files
├── data/                         # Database and data files
├── output/                       # Generated reports and data
├── redundant/                    # Legacy and debug files
├── dev/                          # Development utilities
└── docs/                         # Documentation and examples
```

## 🛠️ Installation

### 1. Prerequisites

- Python 3.10+
- Modern web browser (Chrome/Edge)
- Git

### 2. Setup

```bash
# Clone the repository
git clone https://github.com/DaurenNope/prismind.git
cd prismind

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install
```

### 3. Configuration

```bash
# Copy environment template
cp env_example.txt .env

# Edit .env with your credentials
nano .env
```

Required environment variables:
```env
# AI Services
MISTRAL_API_KEY="your_mistral_key"
GEMINI_API_KEY="your_gemini_key"
PERPLEXITY_API_KEY="your_perplexity_key"

# Social Media (optional)
REDDIT_CLIENT_ID="your_reddit_app_id"
REDDIT_CLIENT_SECRET="your_reddit_secret"
REDDIT_USERNAME="your_reddit_username"
REDDIT_PASSWORD="your_reddit_password"
TWITTER_USERNAME="your_twitter_username"
TWITTER_PASSWORD="your_twitter_password"
THREADS_USERNAME="your_threads_username"
THREADS_PASSWORD="your_threads_password"

# Database
SUPABASE_SERVICE_ROLE_KEY="your_supabase_key"
```

## 🚀 Quick Start

### Option 1: One-Command Launch
```bash
./start.sh
```
This starts the dashboard automatically.

### Option 2: Manual Launch
```bash
# Start dashboard
streamlit run scripts/dashboard.py --server.port 8521
```

### Option 3: Data Collection
```bash
# Collect bookmarks from all platforms
python collect_multi_platform.py
```

## 📊 Usage

### 1. Dashboard Interface
- **Feed**: Browse all posts with filtering and search
- **Browse Categories**: Explore posts by category
- **Full Content View**: View complete post content
- **Platform Filtering**: Filter by Twitter, Reddit, Threads
- **Score Filtering**: Filter by value scores
- **Search**: Search through post content

### 2. Data Collection
- **Twitter**: Extracts bookmarked tweets with media analysis
- **Reddit**: Extracts saved posts and comments
- **Threads**: Extracts saved posts from Threads
- **Multi-Platform**: Orchestrates collection from all platforms

### 3. AI Analysis
- **Content Categorization**: Automatically categorizes posts
- **Value Scoring**: Assigns scores based on content quality
- **Sentiment Analysis**: Analyzes emotional tone
- **Concept Extraction**: Extracts key concepts and tags

## 📁 Project Structure

```
prismind/
├── scripts/                      # Core application scripts
│   ├── dashboard.py              # Streamlit dashboard
│   └── database_manager.py       # Database operations
├── core/                         # Core functionality
│   ├── analysis/                 # AI analysis modules
│   ├── extraction/               # Platform extractors
│   └── learning/                 # Learning systems
├── tests/                        # Comprehensive test suite
│   ├── current_functionality/    # Core functionality tests
│   └── test_core_workflow.py    # Integration tests
├── config/                       # Configuration and cookies
├── data/                         # Database files
├── output/                       # Generated data and reports
├── redundant/                    # Legacy and debug files
├── dev/                          # Development utilities
├── docs/                         # Documentation
└── templates/                    # Templates and examples
```

## 🧪 Testing

The project includes a comprehensive test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/current_functionality/ -v
python -m pytest tests/test_core_workflow.py -v

# Run with coverage
python -m pytest tests/ --cov=core --cov=scripts -v
```

### Test Coverage
- **Dashboard Functionality**: UI components, data display, filtering
- **Data Collection**: Platform extraction, error handling, performance
- **Database Operations**: CRUD operations, schema compatibility
- **AI Analysis**: Content analysis, scoring, categorization
- **Integration**: End-to-end workflow testing

## 🎯 Features in Detail

### Multi-Platform Extraction
- **Twitter**: Extracts bookmarked tweets with media analysis
- **Reddit**: Extracts saved posts and comments with subreddit parsing
- **Threads**: Extracts saved posts from Threads platform
- **Cookie Authentication**: Secure authentication using saved cookies
- **Error Handling**: Robust error handling and retry mechanisms

### AI Analysis Pipeline
- **Primary**: Mistral AI for content categorization and scoring
- **Fallback**: Gemini for backup analysis
- **Perplexity**: Additional AI service for enhanced analysis
- **Value Scoring**: Intelligent content value assessment
- **Concept Extraction**: Automatic tag and concept identification

### Dashboard Features
- **Real-time Data**: Live data from database
- **Advanced Filtering**: Platform, category, score, and search filters
- **Responsive Design**: Mobile-friendly interface
- **Platform-specific Styling**: Distinct visual themes for each platform
- **Full Content View**: Complete post content display

## 🔧 Development

### Code Quality
- **Type Hints**: Comprehensive type annotations
- **Error Handling**: Robust error handling throughout
- **Logging**: Structured logging for debugging
- **Documentation**: Inline documentation and docstrings
- **Testing**: Comprehensive test coverage

### Professional Standards
- **Clean Architecture**: Well-organized code structure
- **Separation of Concerns**: Clear module boundaries
- **Dependency Injection**: Proper dependency management
- **Configuration Management**: Environment-based configuration
- **Security**: Secure credential handling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`python -m pytest tests/ -v`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the documentation in `/docs`
2. Review existing issues on GitHub
3. Create a new issue with detailed information
4. Include test cases for bug reports

## 🚀 Roadmap

- [ ] Enhanced media analysis with local AI models
- [ ] Advanced reporting and analytics
- [ ] Mobile app development
- [ ] API endpoints for external integration
- [ ] Machine learning for personalized recommendations
- [ ] Obsidian integration for knowledge management

---

**PrisMind** - Transform your bookmarks into intelligence! 🧠✨

*Built with ❤️ and AI*
