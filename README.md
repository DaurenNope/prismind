# 🧠 PrisMind - Personal Intelligence Engine

Transform your social media bookmarks into a structured, searchable knowledge base. PrisMind extracts saved content from Twitter, Reddit, and Threads, analyzes your interests with AI, and organizes them into actionable insights.

[![CI](https://github.com/DaurenNope/prismind/actions/workflows/ci.yml/badge.svg)](https://github.com/DaurenNope/prismind/actions/workflows/ci.yml)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Key Features

- **Multi-Platform Extraction**: Pulls saved content from Twitter, Reddit, and Threads
- **AI-Powered Analysis**: Uses Mistral AI, Gemini, and Perplexity to categorize content and extract insights
- **Text Analysis**: Analyzes saved content to extract key information and insights
- **Interactive Dashboard**: Streamlit-based interface for data exploration and control
- **Comprehensive Testing**: Full test suite covering all core functionality
- **Clean Architecture**: Well-structured, maintainable codebase with proper documentation

## 🏗️ Project Structure

```
prismind/
├── config/                      # Configuration files
│   ├── streamlit_secrets.toml   # Streamlit secrets
│   └── *.json                   # Other config files
├── data/                        # Data storage
│   ├── *.db                     # SQLite database files
│   └── *.sql                    # SQL scripts
├── docs/                        # Documentation
│   ├── cleanup_plan_1.md        # Cleanup progress
│   ├── coding_rules_1.md        # Coding standards
│   └── project_roadmap_1.md     # Development roadmap
├── scripts/                     # Utility scripts
│   ├── cleanup_files.py         # File organization
│   ├── organize_root.py         # Root directory cleanup
│   └── update_imports.py        # Import refactoring
├── src/                         # Source code
│   ├── core/                    # Core functionality
│   │   ├── analysis/           # AI analysis
│   │   ├── extraction/         # Data extraction
│   │   └── models/             # Data models
│   ├── services/               # Application services
│   │   ├── database_manager.py # Database operations
│   │   └── collection_service.py # Collection logic
│   ├── web/                    # Web interface
│   │   ├── components/         # UI components
│   │   └── app.py              # Main application
│   └── utils/                  # Utility functions
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   └── integration/            # Integration tests
├── .env.example               # Example environment variables
├── .gitignore                 # Git ignore rules
├── pyproject.toml             # Project metadata
└── requirements.txt           # Python dependencies
```

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/DaurenNope/prismind.git
   cd prismind
   ```

2. **Set up the environment**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   nano .env
   ```

4. **Run the application**
   ```bash
   # Start the Streamlit dashboard
   streamlit run src/web/app.py
   ```

## ⚙️ Configuration

### Environment Variables

- `SAVE_TO_SUPABASE=1`: Push analyzed posts to Supabase
- `OLLAMA_URL=http://localhost:11434`: URL for local Ollama server
- `OLLAMA_MODEL=qwen2.5:7b`: Model to use with Ollama
- `USE_VALUE_SCORER=0`: Disable value scoring
- `ENABLE_LOCAL_FEEDBACK=0`: Disable local feedback learning

## 🧪 Testing

Run the test suite with pytest:

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run with coverage report
pytest --cov=src --cov-report=term-missing
```

## 🛠 Development

### Code Style

We use:
- **Black** for code formatting
- **isort** for import sorting
- **mypy** for static type checking
- **flake8** for linting

Run code quality checks:

```bash
# Format code
black .

# Sort imports
isort .

# Check types
mypy .

# Lint code
flake8 .
```

### Pre-commit Hooks

Install pre-commit hooks to automatically run checks before each commit:

```bash
pip install pre-commit
pre-commit install
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with ❤️ and Python
- Thanks to all contributors who have helped shape this project

## 🔐 Cookie Setup

PrisMind requires cookies to access your saved content:

### Twitter
```bash
python scripts/export_cookies.py twitter
```

### Reddit
```bash
python scripts/export_cookies.py reddit
```

Follow the prompts to log in to each platform. The cookies will be saved to the [cookies/](cookies/) directory.

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

## 🤖 GitHub Automation

To enable automated collection:

1. Set up your secrets in GitHub repository settings:
   ```
   gh secret set REDDIT_COOKIES_JSON < cookies/reddit.json
   gh secret set TWITTER_COOKIES_JSON < cookies/twitter.json
   gh secret set REDDIT_USERNAME --body "your_reddit_username"
   gh secret set TELEGRAM_BOT_TOKEN --body "your_telegram_bot_token"
   gh secret set TELEGRAM_CHAT_ID --body "your_telegram_chat_id"
   ```

2. For additional API-based fallback, set these secrets:
   ```
   gh secret set REDDIT_CLIENT_ID --body "your_reddit_client_id"
   gh secret set REDDIT_CLIENT_SECRET --body "your_reddit_client_secret"
   gh secret set REDDIT_PASSWORD --body "your_reddit_password"
   gh secret set REDDIT_ACCESS_TOKEN --body "your_reddit_access_token"
   gh secret set REDDIT_REFRESH_TOKEN --body "your_reddit_refresh_token"
   gh secret set REDDIT_USER_AGENT --body "your_reddit_user_agent"
   ```

3. The automation runs every 6 hours by default. You can trigger it manually from the GitHub Actions tab.

### Debugging GitHub Automation

If the GitHub automation is not working:

1. Check that all required secrets are set:
   ```bash
   python debug_github_automation.py
   ```

2. Verify the workflow file exists at `.github/workflows/automated-collection.yml`

3. Check the GitHub Actions logs for specific error messages

4. Make sure your cookies are not expired - re-export them periodically:
   ```bash
   python scripts/export_cookies.py
   # Then update the secrets
   gh secret set REDDIT_COOKIES_JSON < cookies/reddit.json
   gh secret set TWITTER_COOKIES_JSON < cookies/twitter.json
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
├── app.py                        # Main application entry point
├── automation_scheduler.py       # Automated collection scheduler
├── collect_multi_platform.py     # Multi-platform collection orchestrator
├── core/                         # Core functionality
│   ├── analysis/                 # AI analysis modules
│   ├── extraction/               # Platform extractors
│   └── learning/                 # Learning systems
├── scripts/                      # Application scripts and utilities
│   ├── dashboard.py              # Streamlit dashboard
│   ├── database_manager.py       # Database operations
│   └── utilities/                # Utility scripts
├── config/                       # Configuration files
│   ├── requirements.txt          # Python dependencies
│   ├── streamlit_secrets*.toml   # Streamlit configuration
│   └── [deployment configs]      # Railway, Render, Vercel configs
├── deploy/                       # Deployment guides and scripts
│   ├── deploy.py                 # Deployment automation
│   ├── DEPLOYMENT_GUIDE.md       # Main deployment guide
│   └── [other deployment docs]   # Various deployment options
├── docs/                         # Documentation
│   ├── BACKEND_ARCHITECTURE.md   # Architecture documentation
│   ├── DESIGN.md                  # Design principles
│   ├── EVOLUTION_PLAN.md         # Future roadmap
│   └── [other docs]              # Various documentation files
├── tests/                        # Comprehensive test suite
├── dev/                          # Development utilities
├── sql/                          # SQL scripts and schemas
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

## 📚 Documentation

### Getting Started
- [User Guide](docs/user_guide.md) - Comprehensive guide to using PrisMind
- [Installation Guide](docs/installation.md) - Step-by-step installation instructions
- [Configuration Reference](docs/configuration_reference.md) - All available configuration options

### Development
- [Development Guide](docs/development/README.md) - Setting up a development environment
- [Coding Standards](docs/development/CODING_STANDARDS.md) - Code style and best practices
- [Testing Guide](docs/testing_guide.md) - How to write and run tests
- [API Reference](docs/api.rst) - Detailed API documentation

### Project
- [Project Roadmap](docs/roadmap.md) - Current status and future plans
- [Architecture](docs/architecture.md) - System architecture and design decisions
- [Release Process](docs/release_process.md) - How we manage releases
- [Code Review Guidelines](docs/code_review_guidelines.md) - Our code review process

### Operations
- [Deployment Guide](docs/deployment_guide.md) - Production deployment instructions
- [Monitoring](docs/monitoring.md) - System monitoring and alerting
- [Backup and Recovery](docs/backup_recovery.md) - Data backup procedures

### Community
- [Contributing Guidelines](CONTRIBUTING.md) - How to contribute to the project
- [Code of Conduct](CODE_OF_CONDUCT.md) - Community guidelines
- [Changelog](CHANGELOG.md) - Release history and changes

## 🆘 Support

For issues and questions:
1. Check the documentation in `/docs`
2. Review deployment guides in `/deploy`
3. Review existing issues on GitHub
4. Create a new issue with detailed information
5. Include test cases for bug reports

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
# Trigger workflow
# Test run Fri Sep  5 23:34:21 WITA 2025
# Test run Fri Sep  5 23:37:01 WITA 2025
# Test run Fri Sep  5 23:44:22 WITA 2025
# Test trigger Sat Sep  6 20:48:28 WITA 2025
# Manual trigger Sat Sep  6 22:40:07 WITA 2025
