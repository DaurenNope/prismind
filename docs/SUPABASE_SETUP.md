# Supabase Setup Guide

## 🚀 Quick Setup

### 1. Create the Database Table

1. **Go to your Supabase dashboard**: https://supabase.com/dashboard
2. **Select your project**
3. **Go to SQL Editor** (left sidebar)
4. **Copy and paste the contents of `scripts/supabase_setup.sql`**
5. **Click "Run"** to create the table

### 2. Test the Connection

Run the test script:
```bash
python3 scripts/supabase_integration.py
```

### 3. Sync Your Data

The script will automatically:
- ✅ Connect to Supabase
- ✅ Find your local SQLite database
- ✅ Sync all posts to Supabase
- ✅ Test data retrieval

## 📊 What Gets Synced

- **All posts** from your local SQLite database
- **AI analysis results** (summaries, tags, categories)
- **Value scores** and categorization
- **Original content** and metadata

## 🔄 Continuous Sync

After initial setup, you can:
- **Add new posts** to Supabase automatically
- **Update existing posts** when AI analysis runs
- **Query from Supabase** instead of local SQLite

## 🛠️ Troubleshooting

### Connection Issues
- Check your `.env` file has correct `SUPABASE_URL` and `SUPABASE_API_KEY`
- Verify the table was created successfully in Supabase dashboard

### Data Issues
- The script handles duplicates automatically
- Posts are updated if they already exist in Supabase
- New posts are inserted with their original IDs

## 🎯 Next Steps

1. **Test the sync** with your current data
2. **Verify data integrity** in Supabase dashboard
3. **Integrate with your dashboard** for real-time updates
4. **Set up automated sync** for new posts

## 📈 Benefits

- **Cloud backup** of all your data
- **Multi-device access** to your bookmarks
- **Better performance** for large datasets
- **Real-time collaboration** (future feature)
- **Advanced analytics** (future feature) 