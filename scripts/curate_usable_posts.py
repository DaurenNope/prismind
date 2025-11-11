"""
Curate usable_posts table with strict criteria.
Only includes truly evergreen posts (<6 months) and fresh time-sensitive posts (≤7 days).
"""

import sqlite3
import sys
import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.manager import SupabaseManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_supabase_client():
    """Get Supabase client"""
    try:
        return SupabaseManager().client
    except Exception as e:
        logger.error(f"Failed to get Supabase client: {e}")
        return None


def parse_datetime(date_str):
    """Parse datetime from various formats"""
    if not date_str:
        return None
    
    if isinstance(date_str, datetime):
        return date_str
    
    try:
        # Try ISO format
        if 'T' in str(date_str):
            return datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        # Try other formats
        return datetime.strptime(str(date_str)[:19], '%Y-%m-%d %H:%M:%S')
    except Exception:
        return None


def check_content_quality(post: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Check if content is complete, not truncated, and properly collected.
    Aggressively filters out error pages, scraping failures, and truncated content.
    
    Returns:
        (is_valid, error_message)
    """
    content = post.get('content', '') or ''
    ai_summary = post.get('ai_summary', '') or ''
    title = post.get('title', '') or ''
    
    # 1. Check for empty content
    if not content or len(content.strip()) < 50:
        return False, "Content is empty or too short (<50 chars)"
    
    content_lower = content.lower()
    content_stripped = content.strip()
    
    # 2. Check for scraping errors and error pages
    # These are critical - they indicate the content was not properly collected
    error_page_patterns = [
        'javascript is not available',
        "we've detected that javascript",
        'please enable javascript',
        'switch to a supported browser',
        'something went wrong',
        "don't fret",
        'try again',
        'privacy related extensions',
        'disable them and try again',
        'x.com links like help center',
        'terms of service',
        'privacy policy',
        'ads info',
        '© 2025 x corp',
        'error loading',
        'failed to load',
        'content not available',
        'scraping failed',
        'extraction failed',
        'could not extract',
        'error extracting',
        'failed to scrape',
        'page not found',
        '404',
        '403 forbidden',
        'access denied',
        'rate limited',
        'too many requests',
    ]
    
    # Check if content starts with or contains error page text
    # Error pages often have these patterns in the first part of the content
    content_start = content_lower[:500]  # First 500 chars are most important
    error_count = sum(1 for pattern in error_page_patterns if pattern in content_lower)
    
    if any(pattern in content_start for pattern in error_page_patterns):
        # Additional check: if content has multiple error patterns, it's definitely an error page
        if error_count >= 2:
            return False, "Content appears to be an error page or scraping failure"
        # Single pattern might be false positive, but check context
        # If content is short (<300 chars) and has error pattern, likely an error page
        if len(content) < 300 and error_count >= 1:
            return False, "Content appears to be an error page (short content with error pattern)"
    
    # 3. Check for placeholder/error content
    placeholder_patterns = [
        'placeholder',
        'undefined',
        'null',
        '[deleted]',
        '[removed]',
        'this content is not available',
        'content unavailable',
        'unavailable',
    ]
    
    if any(pattern in content_lower for pattern in placeholder_patterns):
        return False, "Content appears to be placeholder or error message"
    
    # 4. Check for truncated content (more aggressive detection)
    # Truncation indicators at the end
    truncation_end_patterns = [
        content_stripped.endswith('...'),
        content_stripped.endswith('…'),
        content_stripped.endswith('[truncated]'),
        content_stripped.endswith('[...]'),
        content_stripped.endswith('…'),
    ]
    
    # Check for truncation markers in last 30 chars (more aggressive)
    truncation_in_last_chars = (
        '...' in content_stripped[-30:] or
        '…' in content_stripped[-30:] or
        '[truncated]' in content_stripped[-30:] or
        '[...]' in content_stripped[-30:]
    )
    
    if any(truncation_end_patterns) or truncation_in_last_chars:
        return False, "Content is truncated (ends with truncation marker)"
    
    # 5. Check for mid-sentence/mid-word endings (indicates truncation)
    # More comprehensive check for suspicious endings
    if len(content) >= 100:  # Only check longer content
        last_char = content_stripped[-1] if content_stripped else ''
        last_50_chars = content_stripped[-50:]
        last_words = last_50_chars.split()
        
        # Check if ends without proper sentence punctuation
        proper_endings = '.!?")\'」'
        if last_char not in proper_endings and not truncation_in_last_chars:
            # Check if it ends mid-word (last word is very long or incomplete)
            if last_words:
                last_word = last_words[-1]
                # Very long last word (>20 chars) might indicate truncation
                if len(last_word) > 20:
                    return False, "Content appears truncated (ends with very long word)"
                
                # Check if last word looks incomplete (no vowels in last 5 chars, etc.)
                # This is a heuristic for truncated words
                if len(last_word) > 10:
                    last_part = last_word[-5:].lower()
                    # If last part has no vowels and is >5 chars, might be truncated
                    if len(last_part) >= 5 and not any(v in last_part for v in 'aeiou'):
                        return False, "Content appears truncated (ends with incomplete word)"
        
        # Check for abrupt endings (no punctuation, ends mid-phrase)
        # If content is 200-800 chars and ends without punctuation, suspicious
        if 200 <= len(content) <= 800:
            if last_char not in proper_endings and not truncation_in_last_chars:
                # Check if last "sentence" is very short (might be cut off)
                # Split by sentence endings to see if last sentence is incomplete
                sentences = re.split(r'[.!?]', content_stripped)
                if sentences:
                    last_sentence = sentences[-1].strip()
                    # If last sentence is <20 chars and content doesn't end with punctuation, likely truncated
                    if len(last_sentence) < 20 and last_char not in proper_endings:
                        return False, "Content appears truncated (ends with incomplete sentence)"
    
    # 6. Check for HTML/technical content that shouldn't be in post content
    html_patterns = [
        '<script',
        '<style',
        '<div',
        '<span',
        'href=',
        'src=',
        'class=',
        'id=',
        'javascript:',
    ]
    
    # If content has multiple HTML patterns, it's likely HTML/scraping artifact
    html_count = sum(1 for pattern in html_patterns if pattern in content_lower)
    if html_count >= 3:
        return False, "Content appears to contain HTML/scraping artifacts"
    
    # 7. Check for suspiciously short content (might be incomplete)
    # But allow very short posts if they're complete (e.g., tweet-like content)
    if len(content) < 100:
        # Very short content is OK if it ends properly
        if content_stripped and content_stripped[-1] not in '.!?")\'」':
            # Doesn't end properly - might be truncated
            return False, "Content is too short and doesn't end properly (likely truncated)"
    
    # 8. Check AI summary quality
    if not ai_summary or len(ai_summary.strip()) < 50:
        return False, "AI summary is missing or too short"
    
    # Check if AI summary is wrapped in JSON (extract clean summary)
    clean_summary = ai_summary
    if ai_summary.strip().startswith('```json') or ai_summary.strip().startswith('{'):
        try:
            import json
            if '```json' in ai_summary:
                json_start = ai_summary.find('{')
                json_end = ai_summary.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    summary_json = json.loads(ai_summary[json_start:json_end])
                    clean_summary = summary_json.get('ai_summary', ai_summary)
            elif ai_summary.strip().startswith('{'):
                summary_json = json.loads(ai_summary)
                clean_summary = summary_json.get('ai_summary', ai_summary)
        except:
            # If JSON parsing fails, use original summary
            clean_summary = ai_summary
    
    # Check if clean summary is valid
    if not clean_summary or len(clean_summary.strip()) < 50:
        return False, "AI summary is invalid or too short after JSON extraction"
    
    # Check if AI summary indicates error content
    # If AI summary mentions "error", "JavaScript", "browser", etc., might be error page
    summary_lower = clean_summary.lower()
    error_summary_patterns = [
        'javascript error',
        'error preventing access',
        'browser error',
        'page error',
        'loading error',
        'scraping error',
        'extraction error',
    ]
    
    # If AI summary has error patterns AND content has error patterns, definitely error page
    summary_has_error = any(pattern in summary_lower for pattern in error_summary_patterns)
    if summary_has_error and error_count >= 1:
        return False, "Content and AI summary indicate error page/scraping failure"
    
    # Update post with clean summary for later use
    post['ai_summary_clean'] = clean_summary
    
    # 9. Check title quality (if present)
    if title:
        # Title should not be too long (might be content, not title)
        if len(title) > 500:
            return False, "Title is too long (might be content, not title)"
        # Title should not be empty or just whitespace
        if len(title.strip()) == 0:
            # Empty title is fine - not all posts have titles
            pass
    
    # 10. Final check: Content should look like actual post content
    # If content has very few words relative to length, might be garbage
    words = content_stripped.split()
    if len(words) < 10 and len(content) > 200:
        return False, "Content has too few words for its length (likely garbage data)"
    
    return True, None


def check_time_sensitive_keywords(content: str, ai_summary: str) -> bool:
    """
    Check if content contains time-sensitive keywords that suggest it's not truly evergreen.
    
    Returns:
        True if content appears time-sensitive (should not be marked as evergreen)
    """
    text = (content + ' ' + ai_summary).lower()
    
    # Time-sensitive keywords
    time_sensitive_patterns = [
        # Breaking news
        'breaking',
        'breaking news',
        'just in',
        'developing',
        
        # Recent events
        'released this week',
        'just released',
        'just announced',
        'announced today',
        'launched today',
        'this week',
        'this month',
        'recently',
        'latest',
        
        # Time references
        'yesterday',
        'today',
        'tomorrow',
        'this morning',
        'this afternoon',
        'this evening',
        'hours ago',
        'days ago',
        'weeks ago',
        'just now',
        
        # Urgent language
        'urgent',
        'asap',
        'immediate',
        'right now',
        'currently',
        'happening now',
        
        # News events
        'election',
        'vote',
        'poll',
        'results',
        'outcome',
        'decision',
        'verdict',
        'trial',
        'court',
        'hearing',
        
        # Product launches
        'launch',
        'release',
        'unveiled',
        'debuted',
        'introduced',
        'premiered',
        
        # Market events
        'market opens',
        'trading',
        'stock',
        'crypto',
        'bitcoin',
        'ethereum',
        'price',
        'crash',
        'surge',
        'rally',
    ]
    
    # Check for time-sensitive patterns
    # Use word boundaries to avoid false positives
    import re
    
    # High-confidence patterns (definitely time-sensitive)
    high_confidence_patterns = [
        r'\bbreaking\b',
        r'\bbreaking news\b',
        r'\bjust in\b',
        r'\bdeveloping\b',
        r'\breleased this week\b',
        r'\bjust released\b',
        r'\bjust announced\b',
        r'\bannounced today\b',
        r'\blaunched today\b',
        r'\byesterday\b',
        r'\btoday\b',
        r'\btomorrow\b',
        r'\bthis morning\b',
        r'\bthis afternoon\b',
        r'\bthis evening\b',
        r'\bhours ago\b',
        r'\bdays ago\b',
        r'\bweeks ago\b',
        r'\bjust now\b',
        r'\burgent\b',
        r'\basap\b',
        r'\bimmediate\b',
        r'\bright now\b',
        r'\bcurrently\b',
        r'\bhappening now\b',
        r'\belection\b',
        r'\bvote\b',
        r'\bpoll\b',
        r'\bresults\b',
        r'\boutcome\b',
        r'\bdecision\b',
        r'\bverdict\b',
        r'\btrial\b',
        r'\bcourt\b',
        r'\bhearing\b',
        r'\blaunch\b.*\btoday\b',
        r'\brelease\b.*\btoday\b',
        r'\bunveiled\b.*\btoday\b',
        r'\bdebuted\b.*\btoday\b',
        r'\bintroduced\b.*\btoday\b',
        r'\bpremiered\b.*\btoday\b',
        r'\bmarket opens\b',
        r'\btrading\b.*\bnow\b',
        r'\bprice\b.*\b(crash|surge|rally)\b',
    ]
    
    # Check for high-confidence patterns
    for pattern in high_confidence_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    # Medium-confidence patterns (might be time-sensitive, check context)
    medium_confidence_patterns = [
        r'\bthis week\b',
        r'\bthis month\b',
        r'\brecently\b',
        r'\blastest\b',
    ]
    
    # Count medium-confidence patterns
    medium_count = sum(1 for pattern in medium_confidence_patterns if re.search(pattern, text, re.IGNORECASE))
    
    # If multiple medium-confidence patterns, likely time-sensitive
    if medium_count >= 2:
        return True
    
    # Note: Removed 'crypto', 'bitcoin', 'ethereum', 'stock' from patterns
    # as these can be evergreen topics (educational content, analysis, etc.)
    # Only flag if combined with time-sensitive context (e.g., "bitcoin price crash today")
    
    return False


def is_post_usable(post: Dict[str, Any], now: Optional[datetime] = None) -> tuple[bool, Optional[str]]:
    """
    Check if a post meets the strict criteria for usable_posts.
    
    Returns:
        (is_usable, inclusion_reason)
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Exclude DEPRECATED posts
    category = (post.get('category') or '').upper()
    if category == 'DEPRECATED':
        return False, None
    
    # Must have good analysis
    rewrite_score = post.get('rewrite_score') or 0.0
    value_score = post.get('value_score') or 0.0
    quality_score = post.get('quality_score') or 0.0
    
    if rewrite_score <= 0 or value_score <= 0 or quality_score <= 0:
        return False, None
    
    # Must have ai_summary
    if not post.get('ai_summary') or len(post.get('ai_summary', '')) < 50:
        return False, None
    
    # Must have analysis_model
    analysis_model = post.get('analysis_model')
    if not analysis_model or analysis_model not in ('gemini', 'mistral', 'ollama', 'qwen', 'qwen2.5:1.5b', 'qwen2.5:7b'):
        return False, None
    
    # Note: Content quality is checked in get_usable_posts_from_sqlite before calling this function
    # We don't need to check it again here to avoid double-checking
    
    relevance_window = post.get('relevance_window', 'evergreen')
    urgency_score = post.get('urgency_score') or 0.0
    time_sensitive = post.get('time_sensitive', False)
    created_at = post.get('created_at')
    
    # Check if commentary_worthy (manual override)
    commentary_worthy = post.get('commentary_worthy', False)
    if commentary_worthy:
        return True, 'commentary_worthy'
    
    # Check age
    age_info = None
    if created_at:
        try:
            created_dt = parse_datetime(created_at)
            if created_dt:
                if created_dt.tzinfo:
                    now_dt = now if now.tzinfo else datetime.now(created_dt.tzinfo)
                else:
                    now_dt = datetime.now(timezone.utc)
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                
                age_days = (now_dt - created_dt).days
                age_months = age_days / 30.0
                
                age_info = {
                    'days': age_days,
                    'months': age_months
                }
        except Exception:
            pass
    
    # 1. Truly evergreen posts (<6 months, low urgency, not time-sensitive, not NEWS)
    # IMPORTANT: Evergreen posts must be at least 1 week old to verify they're truly timeless
    # Very recent posts (<7 days) can't be verified as "evergreen" - they might just be recent content
    if relevance_window == 'evergreen':
        # Check if it's truly evergreen (not falsely classified)
        is_false_evergreen = False
        
        # High urgency suggests time-sensitive
        if urgency_score >= 0.35:
            is_false_evergreen = True
        
        # Explicitly marked as time-sensitive
        if time_sensitive:
            is_false_evergreen = True
        
        # NEWS category is inherently time-sensitive
        if category == 'NEWS':
            is_false_evergreen = True
        
        # CONTENT ANALYSIS: Check for time-sensitive keywords in "evergreen" content
        # If content contains time-sensitive keywords, it's likely not truly evergreen
        content = post.get('content', '') or ''
        ai_summary = post.get('ai_summary', '') or ''
        if check_time_sensitive_keywords(content, ai_summary):
            is_false_evergreen = True
            logger.debug(f"Post {post.get('post_id')} marked as false evergreen due to time-sensitive keywords")
        
        # Must not be false evergreen
        if is_false_evergreen:
            return False, None
        
        # Check age
        if age_info:
            # Exclude if too old (>=6 months) - use strict comparison
            if age_info['months'] >= 6.0:
                return False, None
            
            # CRITICAL: Require evergreen posts to be at least 1 week old
            # Very recent posts (<7 days) can't be verified as "evergreen"
            # They might just be recent content with low urgency, not truly timeless
            if age_info['days'] < 7:
                return False, None
            
            # Post is at least 1 week old and <6 months - truly evergreen
            return True, 'truly_evergreen'
        else:
            # If age can't be calculated, exclude to be safe
            # We can't verify it's truly evergreen without knowing the age
            return False, None
    
    # 2. Fresh time-sensitive posts (≤7 days)
    elif relevance_window in ('same-day', '24-72h', 'this-week'):
        if age_info:
            if age_info['days'] <= 7:
                return True, 'fresh_time_sensitive'
            else:
                # Time-sensitive posts >7 days are deprecated
                return False, None
        else:
            # If age can't be calculated, exclude to be safe
            return False, None
    
    # 3. Other relevance windows (this-month, etc.) - exclude
    else:
        return False, None


def get_usable_posts_from_sqlite(db_path: str = 'prismind.db') -> List[Dict[str, Any]]:
    """Get all usable posts from SQLite database"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get all posts with analysis
    # Note: SQLite may not have all columns, so we'll select what we can and handle missing columns
    try:
        cur.execute("""
            SELECT 
                post_id, platform, created_at, relevance_window, urgency_score,
                time_sensitive, category, ai_summary, rewrite_score, value_score, quality_score,
                analysis_model, analyzed_at, content, title, url, author, author_handle,
                best_persona_key, best_persona_score, persona_fit_scores, persona_fit_reasons,
                best_persona_reasons, tags, key_concepts, topic, content_type, language,
                embedding, embedding_model, rewrite_readiness, rewrite_reasons, rewrite_risks,
                analysis_confidence
            FROM posts
            WHERE ai_summary IS NOT NULL 
            AND ai_summary != ''
            AND analysis_model IN ('gemini', 'mistral', 'ollama', 'qwen', 'qwen2.5:1.5b', 'qwen2.5:7b')
            ORDER BY created_at DESC
        """)
    except sqlite3.OperationalError as e:
        # Try with fewer columns if some don't exist
        logger.warning(f"Some columns may not exist, trying with basic columns: {e}")
        cur.execute("""
            SELECT 
                post_id, platform, created_at, relevance_window, urgency_score,
                time_sensitive, category, ai_summary, rewrite_score, value_score, quality_score,
                analysis_model, analyzed_at, content, title, url, author, author_handle,
                best_persona_key, best_persona_score, tags, key_concepts, topic
            FROM posts
            WHERE ai_summary IS NOT NULL 
            AND ai_summary != ''
            AND analysis_model IN ('gemini', 'mistral', 'ollama', 'qwen', 'qwen2.5:1.5b', 'qwen2.5:7b')
            ORDER BY created_at DESC
        """)
    
    posts = cur.fetchall()
    usable_posts = []
    excluded_posts = {
        'content_quality': 0,
        'time_sensitive_keywords': 0,
        'other': 0
    }
    now = datetime.now(timezone.utc)
    
    for row in posts:
        post = dict(row)
        # Set default values for missing columns
        post.setdefault('fit_categories', None)
        post.setdefault('commentary_worthy', False)
        post.setdefault('persona_fit_scores', None)
        post.setdefault('persona_fit_reasons', None)
        post.setdefault('best_persona_reasons', None)
        post.setdefault('rewrite_readiness', None)
        post.setdefault('rewrite_reasons', None)
        post.setdefault('rewrite_risks', None)
        post.setdefault('analysis_confidence', None)
        post.setdefault('content_type', None)
        post.setdefault('language', None)
        post.setdefault('embedding', None)
        post.setdefault('embedding_model', None)
        
        # Check content quality first
        content_valid, content_error = check_content_quality(post)
        if not content_valid:
            excluded_posts['content_quality'] += 1
            continue
        
        # Check if usable
        is_usable, inclusion_reason = is_post_usable(post, now)
        
        if is_usable:
            post['inclusion_reason'] = inclusion_reason
            usable_posts.append(post)
        else:
            # Track why it was excluded
            if inclusion_reason is None:
                # Check if it was excluded due to time-sensitive keywords
                content = post.get('content', '') or ''
                ai_summary = post.get('ai_summary', '') or ''
                if check_time_sensitive_keywords(content, ai_summary) and post.get('relevance_window') == 'evergreen':
                    excluded_posts['time_sensitive_keywords'] += 1
                else:
                    excluded_posts['other'] += 1
            else:
                excluded_posts['other'] += 1
    
    conn.close()
    return usable_posts, excluded_posts


def sync_usable_posts_to_supabase(usable_posts: List[Dict[str, Any]], dry_run: bool = False) -> Dict[str, Any]:
    """Sync usable posts to Supabase"""
    supabase = get_supabase_client()
    
    if not supabase:
        logger.error("Supabase client not available")
        return {'success': False, 'error': 'Supabase client not available'}
    
    stats = {
        'total': len(usable_posts),
        'inserted': 0,
        'updated': 0,
        'errors': 0,
        'skipped': 0
    }
    
    if dry_run:
        logger.info(f"DRY RUN: Would sync {stats['total']} usable posts to Supabase")
        return {'success': True, 'dry_run': True, 'stats': stats}
    
    # Clear existing usable_posts (full rebuild)
    try:
        logger.info("Clearing existing usable_posts table...")
        supabase.table('usable_posts').delete().neq('id', 0).execute()
        logger.info("Cleared existing usable_posts table")
    except Exception as e:
        logger.warning(f"Could not clear usable_posts table: {e}")
    
    # Insert usable posts in batches
    batch_size = 100
    for i in range(0, len(usable_posts), batch_size):
        batch = usable_posts[i:i + batch_size]
        
        # Prepare batch data
        batch_data = []
        for post in batch:
            try:
                # Parse JSON fields if they're strings
                persona_fit_scores = post.get('persona_fit_scores')
                if isinstance(persona_fit_scores, str):
                    import json
                    try:
                        persona_fit_scores = json.loads(persona_fit_scores)
                    except:
                        persona_fit_scores = {}
                
                persona_fit_reasons = post.get('persona_fit_reasons')
                if isinstance(persona_fit_reasons, str):
                    import json
                    try:
                        persona_fit_reasons = json.loads(persona_fit_reasons)
                    except:
                        persona_fit_reasons = {}
                
                # Helper function to parse array fields
                def parse_array_field(value):
                    """Parse array field from various formats to Python list or None"""
                    if value is None:
                        return None
                    if isinstance(value, list):
                        return value if value else None  # Empty list becomes None
                    if isinstance(value, str):
                        if not value or value.strip() == '' or value == '[]':
                            return None
                        try:
                            import json
                            parsed = json.loads(value)
                            if isinstance(parsed, list):
                                return parsed if parsed else None
                            # If it's a dict, try to extract array values
                            if isinstance(parsed, dict):
                                return None
                        except:
                            # If JSON parsing fails, try splitting by comma
                            if ',' in value:
                                return [v.strip() for v in value.split(',') if v.strip()]
                            return None
                    return None
                
                # Parse array fields
                tags = parse_array_field(post.get('tags'))
                key_concepts = parse_array_field(post.get('key_concepts'))
                rewrite_reasons = parse_array_field(post.get('rewrite_reasons'))
                rewrite_risks = parse_array_field(post.get('rewrite_risks'))
                best_persona_reasons = parse_array_field(post.get('best_persona_reasons'))
                fit_categories = parse_array_field(post.get('fit_categories'))
                
                # Prepare data for insertion
                data = {
                    'post_id': post.get('post_id'),
                    'platform': post.get('platform'),
                    'content': post.get('content', ''),
                    'title': post.get('title'),
                    'url': post.get('url', ''),
                    'author': post.get('author'),
                    'author_handle': post.get('author_handle'),
                    'created_at': post.get('created_at'),
                    'ai_summary': post.get('ai_summary'),
                    'category': post.get('category'),
                    'fit_categories': fit_categories,
                    'value_score': float(post.get('value_score', 0)),
                    'quality_score': float(post.get('quality_score', 0)),
                    'rewrite_score': float(post.get('rewrite_score', 0)),
                    'relevance_window': post.get('relevance_window', 'evergreen'),
                    'urgency_score': float(post.get('urgency_score', 0)) if post.get('urgency_score') else None,
                    'time_sensitive': bool(post.get('time_sensitive', False)),
                    'best_persona_key': post.get('best_persona_key'),
                    'best_persona_score': float(post.get('best_persona_score', 0)) if post.get('best_persona_score') else None,
                    'persona_fit_scores': persona_fit_scores,
                    'persona_fit_reasons': persona_fit_reasons,
                    'best_persona_reasons': best_persona_reasons,
                    'tags': tags,
                    'key_concepts': key_concepts,
                    'topic': post.get('topic'),
                    'content_type': post.get('content_type'),
                    'language': post.get('language'),
                    'embedding': post.get('embedding'),
                    'embedding_model': post.get('embedding_model'),
                    'rewrite_readiness': post.get('rewrite_readiness'),
                    'rewrite_reasons': rewrite_reasons,
                    'rewrite_risks': rewrite_risks,
                    'analysis_confidence': float(post.get('analysis_confidence', 0)) if post.get('analysis_confidence') else None,
                    'analysis_model': post.get('analysis_model'),
                    'analyzed_at': post.get('analyzed_at'),
                    'inclusion_reason': post.get('inclusion_reason'),
                    'commentary_worthy': bool(post.get('commentary_worthy', False)),
                }
                
                batch_data.append(data)
            except Exception as e:
                logger.error(f"Error preparing post {post.get('post_id')}: {e}")
                stats['errors'] += 1
                continue
        
        # Insert batch
        if batch_data:
            try:
                result = supabase.table('usable_posts').insert(batch_data).execute()
                stats['inserted'] += len(batch_data)
                logger.info(f"Inserted batch {i//batch_size + 1}: {len(batch_data)} posts")
            except Exception as e:
                logger.error(f"Error inserting batch: {e}")
                stats['errors'] += len(batch_data)
    
    logger.info(f"Synced {stats['inserted']} usable posts to Supabase")
    return {'success': True, 'stats': stats}


def main():
    """Main function to curate usable posts"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Curate usable_posts table')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (do not sync to Supabase)')
    parser.add_argument('--db-path', default='prismind.db', help='Path to SQLite database')
    args = parser.parse_args()
    
    logger.info("Starting usable_posts curation...")
    
    # Get usable posts from SQLite
    logger.info("Getting usable posts from SQLite...")
    usable_posts, excluded_posts = get_usable_posts_from_sqlite(args.db_path)
    logger.info(f"Found {len(usable_posts)} usable posts")
    
    # Show breakdown
    by_reason = {}
    for post in usable_posts:
        reason = post.get('inclusion_reason', 'unknown')
        by_reason[reason] = by_reason.get(reason, 0) + 1
    
    logger.info("Breakdown by inclusion reason:")
    for reason, count in sorted(by_reason.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {reason}: {count}")
    
    # Show exclusion stats
    total_analyzed = len(usable_posts) + sum(excluded_posts.values())
    if total_analyzed > 0:
        logger.info(f"\nExclusion statistics:")
        logger.info(f"  Total analyzed: {total_analyzed}")
        logger.info(f"  Usable: {len(usable_posts)} ({len(usable_posts)/total_analyzed*100:.1f}%)")
        logger.info(f"  Excluded - Content quality issues: {excluded_posts['content_quality']} ({excluded_posts['content_quality']/total_analyzed*100:.1f}%)")
        logger.info(f"  Excluded - Time-sensitive keywords: {excluded_posts['time_sensitive_keywords']} ({excluded_posts['time_sensitive_keywords']/total_analyzed*100:.1f}%)")
        logger.info(f"  Excluded - Other reasons: {excluded_posts['other']} ({excluded_posts['other']/total_analyzed*100:.1f}%)")
    
    # Sync to Supabase
    if not args.dry_run:
        logger.info("Syncing to Supabase...")
        result = sync_usable_posts_to_supabase(usable_posts, dry_run=False)
        
        if result['success']:
            logger.info(f"✅ Successfully synced {result['stats']['inserted']} usable posts to Supabase")
        else:
            logger.error(f"❌ Failed to sync: {result.get('error')}")
    else:
        logger.info("DRY RUN: Skipping Supabase sync")
    
    logger.info("Done!")


if __name__ == '__main__':
    main()

