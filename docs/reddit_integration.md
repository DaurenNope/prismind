# Reddit Integration

This document provides an overview of the Reddit integration in the PrisMind application, including setup instructions, API usage, and best practices.

## Overview

The Reddit integration allows PrisMind to fetch and process saved posts from a user's Reddit account. The integration uses the Reddit API via the `praw` Python library.

## Setup Instructions

### Prerequisites

1. A Reddit account
2. A Reddit application (to get API credentials)

### Creating a Reddit Application

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App" at the bottom
3. Fill in the form:
   - **Name**: `PrisMind` (or your preferred name)
   - **App Type**: Choose "script"
   - **Description**: Optional description
   - **About URL**: Your application's website (optional)
   - **Redirect URI**: `http://localhost:8080` (required but not used for script apps)
4. Click "Create App"
5. Note down the following credentials:
   - Client ID (under the app name, looks like `p0caBcDeFgHiJk`)
   - Secret (next to "secret")

### Environment Variables

Create or update your `.env` file with the following variables:

```
# Reddit API Credentials
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
REDDIT_USER_AGENT=platform:app_id:version (e.g., 'prismind:0.0.1')
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
```

## Rate Limits

Reddit's API has the following rate limits:

- **OAuth Clients**: 60 requests per minute
- **Script Apps**: 60 requests per minute
- **User-based Rate Limiting**: Additional limits may apply based on account age and karma

### Best Practices

- Implement proper error handling for rate limit responses (HTTP 429)
- Use the `time.sleep()` function to avoid hitting rate limits
- Cache responses when possible to reduce API calls
- Log API usage to monitor for potential rate limit issues

## Implementation Details

### Authentication

The integration uses OAuth2 with password grant type for authentication. The `RedditExtractor` class handles authentication automatically when you call the `authenticate()` method.

### Fetching Saved Posts

The main functionality is in the `get_saved_posts()` method, which:

1. Authenticates with Reddit (if not already authenticated)
2. Fetches saved posts with pagination support
3. Filters out duplicates based on post IDs
4. Returns a list of `SocialPost` objects

### Database Schema

Saved posts are stored in the `posts` table with the following relevant columns:

- `post_id`: The Reddit post ID (e.g., '1ncgzjy')
- `platform`: Always 'reddit'
- `author`: The Reddit username of the post author
- `content`: The post content (text)
- `created_at`: When the post was created on Reddit
- `url`: The URL to the Reddit post
- `post_type`: The type of post (e.g., 'post', 'comment')
- `is_saved`: Boolean indicating if the post is saved
- `saved_at`: When the post was saved in PrisMind

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify your credentials in the `.env` file
   - Ensure your Reddit account has 2FA disabled (not currently supported)
   - Check if your IP is rate-limited by Reddit

2. **Rate Limit Exceeded**
   - Implement exponential backoff in your code
   - Reduce the frequency of API calls
   - Consider using a proxy or VPN if you're making too many requests from a single IP

3. **Duplicate Posts**
   - The system should automatically filter duplicates based on post IDs
   - If you're seeing duplicates, check the `posts` table for existing entries

## Future Enhancements

1. Support for OAuth2 with refresh tokens
2. Better error handling for temporary Reddit API outages
3. Support for fetching comments and other content types
4. More detailed analytics on saved posts
5. Integration with the web interface for better visualization
