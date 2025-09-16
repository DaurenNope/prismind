# Prismind Project Structure

## Core Components

### Extraction (`/src/core/extraction/`)
- `social_extractor_base.py`: Base class for all social media extractors
- `reddit_extractor.py`: Main Reddit extractor implementation
- `twitter_extractor_playwright.py`: Twitter extractor using Playwright
- `instagram_extractor.py`: Instagram extractor (incomplete)
- `threads_extractor.py`: Threads extractor (incomplete)
- `working_reddit_extractor.py`: Duplicate Reddit extractor (can be removed)

### Analysis (`/src/core/analysis/`)
- `content_analyzer.py`: AI-powered content analysis using Ollama

### Collection (`/src/core/collection/`)
- `unified_collector.py`: Unified collector for multiple platforms

## Services (`/src/services/`)
- Configuration and data services

## Web Interface (`/src/web/`)
- Web components and application code

## Scripts (`/scripts/`)
- Utility and collection scripts

## Tests (`/tests/`)
- Unit, integration, and end-to-end tests

## Configuration (`/config/`)
- Application configuration files

## Data Files
- `.env`: Environment variables
- `requirements.txt`: Python dependencies
- `pyproject.toml`: Project metadata

## Identified Issues
1. Duplicate Reddit extractors (`reddit_extractor.py` and `working_reddit_extractor.py`)
2. Incomplete extractors (Instagram, Threads)
3. Need to verify if all extractors are properly integrated with the unified collector

## Next Steps
1. Remove `working_reddit_extractor.py` since we have a more complete `reddit_extractor.py`
2. Verify and update the unified collector to work with all extractors
3. Document the API and usage examples for each component
