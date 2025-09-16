import time
import socket
import requests
import dns.resolver
import urllib3
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union

import praw
import prawcore
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .social_extractor_base import SocialExtractorBase, SocialPost

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
        
        # Known Reddit IPs
        self.reddit_ips = {
            'oauth.reddit.com': '151.101.1.140',
            'www.reddit.com': '151.101.1.140',
            'api.reddit.com': '151.101.1.140',
            'reddit.com': '151.101.1.140'
        }
        
        # Configure session with retries and custom resolver
        self.session = self._create_retry_session()
        
        # Patch socket.getaddrinfo to use our IP mapping
        self.original_getaddrinfo = socket.getaddrinfo
        socket.getaddrinfo = self._patched_getaddrinfo
        
    def _patched_getaddrinfo(self, *args):
        """Patch getaddrinfo to use our IP mapping."""
        host = args[0]
        if host in self.reddit_ips:
            # Return the IP address directly for Reddit domains
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (self.reddit_ips[host], args[1] if len(args) > 1 else 80))]
        # Fall back to original getaddrinfo for other domains
        return self.original_getaddrinfo(*args)
        
    def _create_retry_session(self, retries=5, backoff_factor=1.0) -> requests.Session:
        """Create a requests session with retry logic and improved timeouts."""
        session = requests.Session()
        
        # More aggressive retry configuration
        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[500, 502, 503, 504, 403, 429, 408, 407],
            allowed_methods=frozenset(['GET', 'POST', 'PUT', 'DELETE']),
            respect_retry_after_header=True
        )
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=10,
            pool_maxsize=10,
            pool_block=False
        )
        
        # Mount the adapter with retry logic
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # Set default timeout and disable SSL verification
        session.verify = False
        session.timeout = (20, 45)  # Increased timeouts: 20s connect, 45s read
        
        # Add default headers
        session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'oauth.reddit.com'  # Always use oauth.reddit.com as host header
        })
        
        return session
        
    def _resolve_reddit_domains(self) -> Dict[str, str]:
        """Resolve Reddit domains using Google's public DNS."""
        domains = {
            'www': 'www.reddit.com',
            'oauth': 'oauth.reddit.com',
            'api': 'api.reddit.com'
        }
        
        resolved = {}
        for name, domain in domains.items():
            try:
                # Use Google's public DNS
                resolver = dns.resolver.Resolver()
                resolver.nameservers = ['8.8.8.8', '8.8.4.4']  # Google's public DNS
                
                # Get A records
                answers = resolver.resolve(domain, 'A')
                ips = [str(ip) for ip in answers]
                resolved[domain] = ips[0]  # Use first IP
                print(f"✅ Resolved {domain} to {ips[0]}")
                
            except Exception as e:
                print(f"❌ Failed to resolve {domain}: {e}")
                
        return resolved
        
    def _test_reddit_connection(self) -> Tuple[bool, str]:
        """Test connection to Reddit's API endpoints."""
        # First try to resolve domains
        resolved_ips = self._resolve_reddit_domains()
        
        # Prepare endpoints to test
        endpoints = []
        
        # Add direct IPs if we resolved them
        if 'www.reddit.com' in resolved_ips:
            endpoints.append(f"https://{resolved_ips['www.reddit.com']}")
        if 'oauth.reddit.com' in resolved_ips:
            endpoints.append(f"https://{resolved_ips['oauth.reddit.com']}")
            
        # Always try the standard domains as fallback
        endpoints.extend([
            'https://www.reddit.com',
            'https://oauth.reddit.com',
            'https://api.reddit.com',
            'https://151.101.1.140',  # Known Reddit IPs as last resort
            'https://151.101.129.140'
        ])
        
        # Remove duplicates while preserving order
        seen = set()
        endpoints = [url for url in endpoints if not (url in seen or seen.add(url))]
        
        print("🔍 Testing Reddit endpoints:", ", ".join(endpoints))
        
        for url in endpoints:
            try:
                # Skip IP addresses in the Host header to avoid SSL errors
                host_header = None
                if url.startswith('https://') and not url[8:].startswith(tuple('0123456789')):
                    host_header = url[8:].split('/')[0]
                
                response = self.session.get(
                    url, 
                    timeout=10,
                    headers={'Host': host_header} if host_header else {}
                )
                if response.status_code == 200:
                    return True, f"Successfully connected to {url}"
            except requests.exceptions.SSLError as e:
                print(f"⚠️ SSL Error with {url}: {e}")
                continue
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Connection error with {url}: {e}")
                continue
                
        return False, "Failed to connect to any Reddit endpoint"
    
    def authenticate(self) -> bool:
        """Authenticate with Reddit API with enhanced error handling and retries."""
        max_retries = 5  # Increased max retries
        retry_delay = 3  # Increased initial delay to 3 seconds
        
        for attempt in range(max_retries):
            try:
                # Try OAuth2 first if we have a refresh token
                if self.refresh_token:
                    try:
                        print(f"🔑 Attempt {attempt + 1}/{max_retries}: OAuth2 authentication...")
                        self.reddit = praw.Reddit(
                            client_id=self.client_id,
                            client_secret=self.client_secret,
                            refresh_token=self.refresh_token,
                            user_agent=self.user_agent,
                            requestor_kwargs={
                                'session': self.session,
                                'timeout': 30
                            },
                            api_url='https://151.101.1.140/api/v1',
                            oauth_url='https://151.101.1.140/api/v1/access_token',
                            reddit_url='https://151.101.1.140',
                            check_for_async=False
                        )
                        # Test the connection with a simple API call
                        self.reddit.user.me()
                        print("✅ OAuth2 authentication successful")
                        return True
                    except Exception as e:
                        print(f"⚠️ OAuth2 attempt {attempt + 1} failed: {e}")
                        if "invalid_grant" in str(e).lower():
                            print("⚠️ Refresh token may be invalid or expired")
                            break  # No point in retrying with invalid token
                
                # Fall back to password auth if username/password are provided
                if self.username and self.password:
                    try:
                        print(f"🔑 Attempt {attempt + 1}/{max_retries}: Password authentication...")
                        self.reddit = praw.Reddit(
                            client_id=self.client_id,
                            client_secret=self.client_secret,
                            username=self.username,
                            password=self.password,
                            user_agent=self.user_agent,
                            requestor_kwargs={
                                'session': self.session,
                                'timeout': 30
                            },
                            check_for_async=False
                        )
                        # Test the connection with a simple API call
                        self.reddit.user.me()
                        self.read_only_mode = False  # Set read_only_mode to False after successful auth
                        print("✅ Password authentication successful")
                        return True
                    except Exception as e:
                        print(f"⚠️ Password authentication attempt {attempt + 1} failed: {e}")
                
                # If we get here, all auth methods have been tried and failed
                if attempt < max_retries - 1:
                    print(f"🔄 Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                
            except Exception as e:
                print(f"⚠️ Unexpected error during authentication attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    print("❌ All authentication attempts failed")
        
        # If all else fails, try read-only mode
        print("⚠️ Falling back to read-only mode...")
        return self._fallback_to_readonly()
    
    def _fallback_to_readonly(self) -> bool:
        """Fallback to read-only mode when OAuth fails"""
        try:
            print("🔄 Falling back to read-only mode...")
            try:
                # First try with standard endpoint
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent,
                    requestor_kwargs={
                        'session': self.session,
                        'api_url': 'https://151.101.1.140/api/v1',
                        'oauth_url': 'https://151.101.1.140/api/v1/access_token',
                        'reddit_url': 'https://151.101.1.140',
                        'ratelimit_seconds': 5,
                        'min_delay': 1.0
                    },
                    check_for_async=False
                )
                # Test with a simple API call
                subreddit = self.reddit.subreddit("test")
                subreddit.display_name  # This will fail if auth is bad
                print("✅ Reddit read-only authentication successful with direct IP")
                return True
            except Exception as direct_ip_error:
                print(f"⚠️ Direct IP connection failed, trying standard endpoint: {direct_ip_error}")
                # Fall back to standard endpoint
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent,
                    check_for_async=False
                )
                subreddit = self.reddit.subreddit("test")
                subreddit.display_name
                print("✅ Reddit read-only authentication successful with standard endpoint")
                return True
        except Exception as e:
            print(f"❌ Reddit read-only auth failed: {e}")
            return False
    
    def get_saved_posts(self, limit: int = 100, max_retries: int = 3, after: str = None, existing_ids: set = None) -> List[SocialPost]:
        """Get saved posts and comments from Reddit with retries and pagination.
        
        Args:
            limit: Maximum number of posts to return
            max_retries: Maximum number of retry attempts
            after: Fullname of the next data block to return (for pagination)
            existing_ids: Set of post IDs that already exist in the database
            
        Returns:
            Tuple of (List[SocialPost], str): List of new posts and the 'after' token for pagination
        """
        print(f"🔍 Starting get_saved_posts with limit={limit}, after={after}")
        
        if not self.reddit:
            print("⚠️ Reddit client not initialized, attempting to authenticate...")
            if not self.authenticate():
                print("❌ Authentication failed and no read-only access available")
                return [], None
        
        try:
            # Test authentication by getting current user info
            me = self.reddit.user.me()
            print(f"✅ Authenticated as: {me.name}")
            print(f"🔒 Read-only mode: {self.read_only_mode}")
        except Exception as e:
            print(f"❌ Error getting current user: {e}")
            return [], None

        posts = []
        params = {'limit': min(limit, 100)}  # Ensure we don't exceed Reddit's limit of 100
        if after and isinstance(after, str):
            print(f"🔗 Resuming from after: {after}")
            params['after'] = after
            
        for attempt in range(max_retries):
            try:
                saved_items = []
                next_after = None
                
                if self.read_only_mode:
                    print("⚠️ In read-only mode, fetching popular posts instead of saved ones")
                    saved = self.reddit.subreddit("all").hot(limit=limit, params=params)
                    saved_items = list(saved)
                    print(f"ℹ️ Fetched {len(saved_items)} popular posts")
                else:
                    print("🔍 Fetching saved posts...")
                    try:
                        saved = self.reddit.user.me().saved(limit=limit, params=params)
                        saved_items = list(saved)
                        print(f"✅ Fetched {len(saved_items)} saved items")
                        if hasattr(saved, 'after'):
                            next_after = saved.after
                            print(f"➡️ Next page token: {next_after}")
                    except Exception as e:
                        print(f"❌ Error fetching saved posts: {e}")
                        saved_items = []
                    
                # Log details about the first few items
                for i, item in enumerate(saved_items[:3]):  # Log first 3 items
                    try:
                        item_id = getattr(item, 'id', 'N/A')
                        item_name = getattr(item, 'name', 'N/A')
                        item_title = getattr(item, 'title', 'N/A')
                        if item_title != 'N/A':
                            item_title = item_title[:50] + '...' if len(str(item_title)) > 50 else item_title
                        print(f"📝 Item {i+1}: ID={item_id}, Name={item_name}, Title={item_title}")
                    except Exception as e:
                        print(f"⚠️ Error logging item {i}: {e}")
                
                # If we have existing_ids, filter out posts we've already seen
                if existing_ids is not None and saved_items:
                    before_filter = len(saved_items)
                    filtered_items = []
                    existing_base_ids = {str(id_) for id_ in existing_ids}
                    
                    print(f"🔍 Checking against {len(existing_base_ids)} existing posts...")
                    print(f"📝 First few existing IDs: {list(existing_base_ids)[:3]}...")
                    
                    for item in saved_items:
                        try:
                            # Try different ways to get the ID
                            item_id = getattr(item, 'id', None)
                            item_name = getattr(item, 'name', None)
                            
                            # Clean up the IDs for comparison
                            clean_item_id = str(item_id) if item_id else ''
                            clean_item_name = str(item_name).replace('t3_', '') if item_name else ''
                            
                            # Debug log the item being checked
                            debug_info = f"Item ID: {clean_item_id}, Name: {clean_item_name}"
                            if hasattr(item, 'title'):
                                debug_info += f", Title: {getattr(item, 'title', 'No title')}"
                            print(f"🔍 Checking item: {debug_info}")
                            
                            # Only filter if we have a valid ID to compare
                            if clean_item_id and clean_item_id in existing_base_ids:
                                print(f"ℹ️ Filtered out duplicate by ID: {clean_item_id}")
                                continue
                                
                            if clean_item_name and clean_item_name in existing_base_ids:
                                print(f"ℹ️ Filtered out duplicate by name: {clean_item_name}")
                                continue
                                
                            filtered_items.append(item)
                            print(f"✅ Added new item to processing queue: {clean_item_id or clean_item_name}")
                            
                        except Exception as e:
                            print(f"⚠️ Error processing item: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                    
                    saved_items = filtered_items
                    print(f"ℹ️ Kept {len(saved_items)} new posts after filtering (from {before_filter} total)")
                
                # Convert items to SocialPost objects
                print(f"🔄 Converting {len(saved_items)} items to SocialPost objects...")
                for idx, item in enumerate(saved_items, 1):
                    try:
                        item_id = getattr(item, 'id', 'unknown')
                        print(f"🔄 Converting item {idx}/{len(saved_items)} (ID: {item_id})...")
                        
                        # Debug print the item's attributes
                        if hasattr(item, 'title'):
                            print(f"   Title: {getattr(item, 'title', 'No title')}")
                        if hasattr(item, 'author'):
                            print(f"   Author: {getattr(item.author, 'name', 'Unknown')}")
                        
                        post = self._convert_reddit_item(item, is_saved=not self.read_only_mode)
                        if post:
                            posts.append(post)
                            print(f"✅ Successfully converted post {idx}/{len(saved_items)} (ID: {item_id})")
                        else:
                            print(f"⚠️ Conversion returned None for item {idx} (ID: {item_id})")
                            
                    except Exception as e:
                        print(f"⚠️ Error converting item {idx} (ID: {item_id}): {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                        
                print(f"✅ Retrieved {len(posts)} items from Reddit" + (" (read-only mode)" if self.read_only_mode else ""))
                return posts, next_after  # Return both posts and next_after token
                
            except Exception as e:
                print(f"❌ Error during Reddit API call (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)  # Exponential backoff
                    print(f"🔄 Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
        
        print("❌ All retry attempts failed")
        return [], None  # Return empty list and None for next_after on failure
    
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
                
                # Ensure we have a valid URL
                url = f"https://reddit.com{item.permalink}" if hasattr(item, 'permalink') and item.permalink else 'https://reddit.com'
                
                return SocialPost(
                    platform='reddit',
                    post_id=item.id if hasattr(item, 'id') else 'unknown_id',
                    author=str(item.author) if hasattr(item, 'author') and item.author else '[deleted]',
                    author_handle=f"u/{item.author}" if hasattr(item, 'author') and item.author else '[deleted]',
                    content=enhanced_content,
                    created_at=datetime.fromtimestamp(item.created_utc) if hasattr(item, 'created_utc') else datetime.utcnow(),
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
                    folder_category=f"r/{item.subreddit.display_name}" if hasattr(item, 'subreddit') and item.subreddit else 'Unknown'
                )
            elif isinstance(item, praw.models.Comment):  # It's a comment
                # Ensure we have a valid URL
                comment_url = f"https://reddit.com{item.permalink}" if hasattr(item, 'permalink') and item.permalink else 'https://reddit.com'
                
                return SocialPost(
                    platform='reddit_comment',
                    post_id=f"{item.id}" if hasattr(item, 'id') else 'unknown_comment_id',
                    author=str(item.author) if hasattr(item, 'author') and item.author else '[deleted]',
                    author_handle=f"u/{item.author}" if hasattr(item, 'author') and item.author else '[deleted]',
                    content=getattr(item, 'body', '[No content]'),
                    created_at=datetime.fromtimestamp(item.created_utc) if hasattr(item, 'created_utc') else datetime.utcnow(),
                    url=comment_url,
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
        if not submission or not hasattr(submission, 'id'):
            return []
            
        media_urls = set()  # Use a set to avoid duplicates

        try:
            # 1. Direct URL for image/gif
            if hasattr(submission, 'url') and submission.url and isinstance(submission.url, str):
                if any(submission.url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                    media_urls.add(submission.url)
            
            # 2. Reddit Video
            if hasattr(submission, 'is_video') and submission.is_video:
                if hasattr(submission, 'media') and submission.media and isinstance(submission.media, dict):
                    video_data = submission.media.get('reddit_video', {})
                    if isinstance(video_data, dict) and 'fallback_url' in video_data:
                        fallback_url = video_data['fallback_url']
                        if isinstance(fallback_url, str):
                            media_urls.add(fallback_url)

            # 3. Reddit Gallery
            if hasattr(submission, 'is_gallery') and submission.is_gallery:
                if hasattr(submission, 'media_metadata') and submission.media_metadata:
                    for item in submission.media_metadata.values():
                        if not isinstance(item, dict):
                            continue
                        if item.get('status') == 'valid' and 's' in item and isinstance(item['s'], dict):
                            media_url = item['s'].get('u')
                            if isinstance(media_url, str):
                                media_urls.add(media_url.replace('&amp;', '&'))

            # 4. Embedded Media (e.g., YouTube, Gfycat)
            if hasattr(submission, 'media') and submission.media and isinstance(submission.media, dict):
                oembed = submission.media.get('oembed')
                if oembed and isinstance(oembed, dict):
                    thumbnail = oembed.get('thumbnail_url')
                    if isinstance(thumbnail, str):
                        media_urls.add(thumbnail)

            # 5. Preview images (for link posts)
            if hasattr(submission, 'preview') and submission.preview and 'images' in submission.preview:
                for image in submission.preview['images']:
                    if not isinstance(image, dict):
                        continue
                    source = image.get('source', {})
                    if not isinstance(source, dict):
                        continue
                    source_url = source.get('url')
                    if isinstance(source_url, str):
                        media_urls.add(source_url.replace('&amp;', '&'))

        except Exception as e:
            print(f"⚠️ Error extracting media URLs: {e}")

        return list(media_urls)

    def _extract_media_from_comment(self, comment: praw.models.Comment) -> List[str]:
        """Extract media URLs from a Reddit comment (usually GIFs or images)."""
        if not comment or not hasattr(comment, 'id'):
            return []
            
        media_urls = set()
        
        try:
            if hasattr(comment, 'media_metadata') and comment.media_metadata:
                for item in comment.media_metadata.values():
                    if not isinstance(item, dict):
                        continue
                    if item.get('status') == 'valid' and 's' in item and isinstance(item['s'], dict):
                        media_url = item['s'].get('u')
                        if isinstance(media_url, str):
                            media_urls.add(media_url.replace('&amp;', '&'))
        except Exception as e:
            print(f"⚠️ Error extracting media from comment: {e}")
            
        return list(media_urls)