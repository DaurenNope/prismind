# 🚀 PrisMind Startup Guide

## Quick Start Options

### Option 1: Use the Start Script (Recommended)
```bash
./start.sh
```
This will:
- Activate the virtual environment
- Start the dashboard at http://localhost:8509

### Option 2: Manual Start
```bash
# Activate virtual environment
source venv/bin/activate

# Start dashboard
cd scripts && streamlit run dashboard_unified.py --server.port 8509
```

### Option 3: Background Start
```bash
# Activate virtual environment
source venv/bin/activate

# Start in background
cd scripts && nohup streamlit run dashboard_unified.py --server.port 8509 > ../dashboard.log 2>&1 &
```

## After Starting

1. **Open your browser** to: http://localhost:8509
2. **Dashboard Features Available**:
   - View and filter your 192 bookmarks
   - Search with smart filters
   - Rate posts (Gold, 1-5 stars)
   - AI enhance posts
   - Collect new bookmarks
   - Rescrape individual posts

## Additional Scripts

### Collect New Bookmarks
```bash
python collect_bookmarks.py
```

### AI Enhance All Posts
```bash
python enhance_all_simple.py
```

### Setup Twitter (First Time)
```bash
python setup_twitter_config.py
```

## Troubleshooting

### Dashboard Not Starting?
- Check if port 8509 is free: `lsof -i :8509`
- Kill existing process: `pkill -f streamlit`
- Try again: `./start.sh`

### Virtual Environment Issues?
```bash
# Recreate if needed
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

**Your clean, lightweight intelligent bookmark system is ready! 🎉**