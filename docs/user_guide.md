# User Guide

Welcome to PrisMind! This guide will help you get started with using the application.

## Table of Contents
1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Getting Started](#getting-started)
4. [Features](#features)
5. [Troubleshooting](#troubleshooting)
6. [FAQs](#faqs)

## Installation

### Prerequisites
- Python 3.9 or higher
- pip (Python package manager)
- Git (for development)

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/prismind.git
   cd prismind
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Configuration

### Environment Variables

Edit the `.env` file with your configuration:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/prismind
REDIS_URL=redis://localhost:6379/0

# API Keys
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret

# Application Settings
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
```

## Getting Started

### Running the Application

1. **Start the development server**
   ```bash
   python -m streamlit run src/web/app.py
   ```

2. **Access the web interface**
   Open your browser and go to: http://localhost:8501

### Basic Usage

1. **Dashboard**
   - View analytics and metrics
   - Monitor data collection status
   - Access recent activities

2. **Data Collection**
   - Configure data sources
   - Schedule collection jobs
   - Monitor collection progress

3. **Analysis**
   - Run sentiment analysis
   - Generate reports
   - Export data

## Features

### 1. Data Collection
- Collect data from multiple social media platforms
- Schedule recurring collections
- Filter content by keywords, users, or hashtags

### 2. Data Analysis
- Sentiment analysis
- Topic modeling
- Trend detection
- Custom analytics

### 3. Data Visualization
- Interactive dashboards
- Custom reports
- Export to multiple formats (CSV, JSON, PDF)

### 4. Alerts and Notifications
- Set up custom alerts
- Email notifications
- Webhook integrations

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Verify API keys and tokens
   - Check internet connection
   - Ensure the service is running

2. **Installation Issues**
   - Ensure all dependencies are installed
   - Check Python version
   - Try recreating the virtual environment

3. **Performance Issues**
   - Check system resources
   - Optimize database queries
   - Enable caching

### Getting Help

If you encounter any issues:
1. Check the [FAQ](#faqs) section
2. Search the [GitHub Issues](https://github.com/yourusername/prismind/issues)
3. [Open a new issue](https://github.com/yourusername/prismind/issues/new)

## FAQs

### General

**Q: What platforms does PrisMind support?**
A: Currently supports Twitter, Reddit, and custom API integrations.

**Q: Is there a free trial available?**
A: Yes, you can try PrisMind with limited features for free.

### Technical

**Q: What are the system requirements?**
A: Minimum 4GB RAM, 2 CPU cores, 10GB disk space.

**Q: How do I back up my data?**
A: Regular database backups are recommended. See the admin guide for details.

### Billing

**Q: What payment methods do you accept?**
A: We accept all major credit cards and PayPal.

**Q: Can I upgrade or downgrade my plan?**
A: Yes, you can change your plan at any time.

## Support

For additional help, please contact support@prismind.ai
