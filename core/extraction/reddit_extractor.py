import time
from datetime import datetime
from typing import Dict, List

import praw
import prawcore

from .social_extractor_base import SocialExtractorBase, SocialPost


class RedditExtractor(SocialExtractorBase):
    """Extract saved posts and comments from Reddit"""
    
    def __init__(self, client_id: str, client_secret: str, user_agent: str, username: str = None, password: str = None, access_token: str = None, refresh_token: str = None):
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.username = username
        self.password = password
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.reddit = None
        self.read_only_mode = not (username and password) and not access_token
    
    def authenticate(self) -> bool:
        """Authenticate with Reddit API, providing specific error handling."""
        if self.read_only_mode:
            print("🔍 Reddit read-only mode (no username/password provided)")
            try:
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent,
                    check_for_async=False
                )
                # Test with a simple API call
                subreddit = self.reddit.subreddit("test")
                subreddit.display_name  # This will fail if auth is bad
                print("✅ Reddit read-only authentication successful")
                return True
            except Exception as read_only_error:
                print(f"❌ Reddit read-only auth failed: {read_only_error}")
                return False
        
        # Try OAuth2 authentication first (if tokens are available)
        if self.access_token and self.refresh_token:
            try:
                print("🔍 Reddit OAuth2 authentication")
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent,
                    access_token=self.access_token,
                    refresh_token=self.refresh_token,
                    check_for_async=False
                )
                
                # Test authentication
                user = self.reddit.user.me()
                if user:
                    print(f"✅ Reddit OAuth2 authenticated as: {user.name}")
                    return True
                else:
                    print("❌ Reddit OAuth2 authentication failed: Could not retrieve user.")
                    return False
                    
            except Exception as oauth_error:
                print(f"❌ Reddit OAuth2 error: {oauth_error}")
                
                # Check if it's a network connectivity issue
                if "NameResolutionError" in str(oauth_error) or "oauth.reddit.com" in str(oauth_error):
                    print("🌐 Network connectivity issue detected")
                    print("🔄 Trying alternative Reddit endpoints...")
                    
                    # Try with different Reddit configuration
                    try:
                        import requests
                        # Test if we can reach Reddit at all
                        response = requests.get("https://www.reddit.com", timeout=10)
                        if response.status_code == 200:
                            print("✅ Reddit main site is accessible")
                            print("⚠️ OAuth endpoint has DNS issues - this is temporary")
                            print("🔄 Falling back to read-only mode for now...")
                            return self._fallback_to_readonly()
                        else:
                            print(f"❌ Reddit main site returned: {response.status_code}")
                    except Exception as network_error:
                        print(f"❌ Network test failed: {network_error}")
                
                print("🔄 Falling back to password authentication...")
                # Continue to password authentication below
        
        # Try password-based authentication (if OAuth2 failed or not available)
        if self.username and self.password:
            try:
                print("🔍 Reddit password authentication")
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent,
                    username=self.username,
                    password=self.password,
                    check_for_async=False
                )
                
                # Test authentication
                user = self.reddit.user.me()
                if user:
                    print(f"✅ Reddit authenticated as: {user.name}")
                    return True
                else:
                    print("❌ Reddit authentication failed: Could not retrieve user.")
                    return False
                    
            except praw.exceptions.RedditAPIException as e:
                print(f"❌ Reddit API error: {e}")
                # Try without password (read-only mode)
                try:
                    print("🔄 Trying read-only authentication...")
                    self.reddit = praw.Reddit(
                        client_id=self.client_id,
                        client_secret=self.client_secret,
                        user_agent=self.user_agent,
                        check_for_async=False
                    )
                    # Test with a simple API call
                    subreddit = self.reddit.subreddit("test")
                    subreddit.display_name  # This will fail if auth is bad
                    print("✅ Reddit read-only authentication successful")
                    return True
                except Exception as read_only_error:
                    print(f"❌ Reddit read-only auth also failed: {read_only_error}")
                    return False
    
    def _fallback_to_readonly(self) -> bool:
        """Fallback to read-only mode when OAuth fails"""
        try:
            print("🔍 Reddit read-only fallback")
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
                check_for_async=False
            )
            # Test with a simple API call
            subreddit = self.reddit.subreddit("test")
            subreddit.display_name  # This will fail if auth is bad
            print("✅ Reddit read-only fallback successful")
            self.read_only_mode = True
            return True
        except Exception as read_only_error:
            print(f"❌ Reddit read-only fallback failed: {read_only_error}")
            return False
    
    def get_saved_posts(self, limit: int = 100, max_retries: int = 3) -> List[SocialPost]:
        """Get saved posts and comments from Reddit with retries."""
        if not self.reddit:
            if not self.authenticate():
                raise Exception("Authentication with Reddit failed")

        if self.read_only_mode:
            print("⚠️ Cannot access saved posts in read-only mode. Returning empty list.")
            return []

        posts = []
        for attempt in range(max_retries):
            try:
                saved_items = self.reddit.user.me().saved(limit=limit)
                for item in saved_items:
                    post = self._convert_reddit_item(item)
                    if post:
                        posts.append(post)
                print(f"✅ Retrieved {len(posts)} saved items from Reddit")
                return posts # Success
            except prawcore.exceptions.PrawcoreException as e:
                print(f"❌ Reddit API error on attempt {attempt + 1}: {e}")
                if attempt >= max_retries - 1:
                    print("❌ All retries failed for getting saved posts.")
                    break
                time.sleep(2 * (attempt + 1))
            except Exception as e:
                print(f"❌ An unexpected error occurred: {e}")
                break # Don't retry on unexpected errors
        return posts
    
    def get_liked_posts(self, limit: int = 100, max_retries: int = 3) -> List[SocialPost]:
        """Get upvoted posts from Reddit with retries."""
        if not self.reddit:
            if not self.authenticate():
                raise Exception("Authentication with Reddit failed")

        if self.read_only_mode:
            print("⚠️ Cannot access liked posts in read-only mode. Returning empty list.")
            return []

        posts = []
        for attempt in range(max_retries):
            try:
                upvoted_items = self.reddit.user.me().upvoted(limit=limit)
                for item in upvoted_items:
                    post = self._convert_reddit_item(item, is_saved=False)
                    if post:
                        posts.append(post)
                print(f"✅ Retrieved {len(posts)} upvoted items from Reddit")
                return posts # Success
            except prawcore.exceptions.PrawcoreException as e:
                print(f"❌ Reddit API error on attempt {attempt + 1}: {e}")
                if attempt >= max_retries - 1:
                    print("❌ All retries failed for getting upvoted posts.")
                    break
                time.sleep(2 * (attempt + 1))
            except Exception as e:
                print(f"❌ An unexpected error occurred: {e}")
                break # Don't retry on unexpected errors
        return posts
    
    def get_top_comments(self, submission_id: str, limit: int = 5) -> List[Dict]:
        """Get top valuable comments for a Reddit submission"""
        try:
            submission = self.reddit.submission(id=submission_id)
            submission.comments.replace_more(limit=0)
            
            # Get top-level comments sorted by score
            top_comments = []
            all_comments = submission.comments.list()[:50]  # Get more to filter from
            
            # Sort by score and filter valuable ones
            for comment in sorted(all_comments, key=lambda x: getattr(x, 'score', 0), reverse=True):
                if (hasattr(comment, 'body') and 
                    comment.body not in ['[deleted]', '[removed]'] and
                    len(comment.body.strip()) > 30 and  # Meaningful length
                    getattr(comment, 'score', 0) > 2):  # Some engagement
                    
                    top_comments.append({
                        'author': str(comment.author) if comment.author else 'Unknown',
                        'content': comment.body,
                        'score': getattr(comment, 'score', 0),
                        'created_at': datetime.fromtimestamp(comment.created_utc).isoformat(),
                        'is_op': getattr(comment, 'is_submitter', False),
                        'depth': getattr(comment, 'depth', 0),
                        'url': f"https://reddit.com{comment.permalink}"
                    })
                    
                    if len(top_comments) >= limit:
                        break
            
            return top_comments
            
        except Exception as e:
            print(f"❌ Error extracting comments for {submission_id}: {e}")
            return []
    
    def _convert_reddit_item(self, item, is_saved: bool = True) -> SocialPost:
        """Convert Reddit submission or comment to SocialPost"""
        try:
            # Handle both submissions (posts) and comments
            if isinstance(item, praw.models.Submission):  # It's a submission
                # Extract top comments immediately during scraping
                top_comments = self.get_top_comments(item.id, limit=5)
                
                # Build enhanced content with valuable comments
                enhanced_content = f"{item.title}\n\n{item.selftext}" if item.selftext else item.title
                
                if top_comments:
                    enhanced_content += "\n\n=== TOP VALUABLE COMMENTS ===\n"
                    for i, comment in enumerate(top_comments, 1):
                        enhanced_content += f"\n💬 Comment {i} (Score: {comment['score']}) by {comment['author']}:\n"
                        enhanced_content += f"{comment['content']}\n"
                
                return SocialPost(
                    platform='reddit',
                    post_id=item.id,
                    author=str(item.author) if item.author else '[deleted]',
                    author_handle=f"u/{item.author}" if item.author else '[deleted]',
                    content=enhanced_content,
                    created_at=datetime.fromtimestamp(item.created_utc),
                    url=f"https://reddit.com{item.permalink}",
                    post_type='post',
                    media_urls=self._extract_media_urls(item),
                    hashtags=[],  # Reddit doesn't have hashtags
                    mentions=[],  # Could parse mentions from text
                    engagement={
                        'score': item.score,
                        'upvote_ratio': getattr(item, 'upvote_ratio', 0),
                        'num_comments': item.num_comments
                    },
                    is_saved=is_saved,
                    saved_at=datetime.now() if is_saved else None,
                    folder_category=f"r/{item.subreddit.display_name}"
                )
            elif isinstance(item, praw.models.Comment):  # It's a comment
                return SocialPost(
                    platform='reddit',
                    post_id=item.id,
                    author=str(item.author) if item.author else '[deleted]',
                    author_handle=f"u/{item.author}" if item.author else '[deleted]',
                    content=item.body,
                    created_at=datetime.fromtimestamp(item.created_utc),
                    url=f"https://reddit.com{item.permalink}",
                    post_type='comment',
                    media_urls=self._extract_media_from_comment(item),
                    hashtags=[],
                    mentions=[],
                    engagement={
                        'score': item.score,
                        'replies': len(item.replies) if hasattr(item.replies, '__len__') else 0
                    },
                    is_saved=is_saved,
                    saved_at=datetime.now() if is_saved else None,
                    folder_category=f"r/{item.subreddit.display_name}"
                )
                
        except Exception as e:
            print(f"❌ Error converting Reddit item: {e}")
            return None
    
    def _extract_media_urls(self, submission: praw.models.Submission) -> List[str]:
        """Extract media URLs from a Reddit submission, including galleries, videos, and images."""
        media_urls = set() # Use a set to avoid duplicates

        # 1. Direct URL for image/gif
        if hasattr(submission, 'url') and submission.url:
            if any(submission.url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                media_urls.add(submission.url)
        
        # 2. Reddit Video
        if hasattr(submission, 'is_video') and submission.is_video:
            if hasattr(submission, 'media') and submission.media and 'reddit_video' in submission.media:
                media_urls.add(submission.media['reddit_video']['fallback_url'])

        # 3. Reddit Gallery
        if hasattr(submission, 'is_gallery') and submission.is_gallery:
            if hasattr(submission, 'media_metadata'):
                for item in submission.media_metadata.values():
                    if item.get('status') == 'valid' and 's' in item and 'u' in item['s']:
                        media_urls.add(item['s']['u'].replace('&amp;', '&'))

        # 4. Embedded Media (e.g., YouTube, Gfycat)
        if hasattr(submission, 'media') and submission.media and 'oembed' in submission.media and submission.media['oembed']:
            # For videos, we can often get a thumbnail
            thumbnail = submission.media['oembed'].get('thumbnail_url')
            if thumbnail:
                media_urls.add(thumbnail)

        # 5. Preview images (for link posts)
        if hasattr(submission, 'preview') and 'images' in submission.preview:
            for image in submission.preview['images']:
                source_url = image.get('source', {}).get('url')
                if source_url:
                    media_urls.add(source_url.replace('&amp;', '&'))

        return list(media_urls)

    def _extract_media_from_comment(self, comment: praw.models.Comment) -> List[str]:
        """Extract media URLs from a Reddit comment (usually GIFs or images)."""
        media_urls = set()
        if hasattr(comment, 'media_metadata'):
            for item in comment.media_metadata.values():
                if item.get('status') == 'valid' and 's' in item and 'u' in item['s']:
                     media_urls.add(item['s']['u'].replace('&amp;', '&'))
        return list(media_urls) 