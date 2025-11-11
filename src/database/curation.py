#!/usr/bin/env python3
"""
Database Curation Module

Handles automatic curation of posts to usable_posts table based on quality and usability criteria.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseCuration:
    """Handles automatic post curation to usable_posts"""

    def __init__(self, supabase=None):
        self._supabase = supabase

    def _check_content_quality_for_curation(self, post: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if content is complete, not truncated, and properly collected.
        More comprehensive than _check_data_quality - this is for curation to usable_posts.
        Same logic as in curate_usable_posts.py
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
        error_page_patterns = [
            'javascript is not available', "we've detected that javascript", 'please enable javascript',
            'switch to a supported browser', 'something went wrong', "don't fret", 'try again',
            'privacy related extensions', 'disable them and try again', 'x.com links like help center',
            'terms of service', 'privacy policy', 'ads info', '© 2025 x corp', 'error loading',
            'failed to load', 'content not available', 'scraping failed', 'extraction failed',
            'could not extract', 'error extracting', 'failed to scrape', 'page not found', '404',
            '403 forbidden', 'access denied', 'rate limited', 'too many requests',
        ]
        
        content_start = content_lower[:500]
        error_count = sum(1 for pattern in error_page_patterns if pattern in content_lower)
        
        if any(pattern in content_start for pattern in error_page_patterns):
            if error_count >= 2:
                return False, "Content appears to be an error page or scraping failure"
            if len(content) < 300 and error_count >= 1:
                return False, "Content appears to be an error page (short content with error pattern)"
        
        # 3. Check for placeholder/error content
        placeholder_patterns = [
            'placeholder', 'undefined', 'null', '[deleted]', '[removed]',
            'this content is not available', 'content unavailable', 'unavailable',
        ]
        
        if any(pattern in content_lower for pattern in placeholder_patterns):
            return False, "Content appears to be placeholder or error message"
        
        # 4. Check for truncated content
        truncation_end_patterns = [
            content_stripped.endswith('...'), content_stripped.endswith('…'),
            content_stripped.endswith('[truncated]'), content_stripped.endswith('[...]'),
        ]
        truncation_in_last_chars = (
            '...' in content_stripped[-30:] or '…' in content_stripped[-30:] or
            '[truncated]' in content_stripped[-30:] or '[...]' in content_stripped[-30:]
        )
        
        if any(truncation_end_patterns) or truncation_in_last_chars:
            return False, "Content is truncated (ends with truncation marker)"
        
        # 5. Check for mid-sentence/mid-word endings
        if len(content) >= 100:
            last_char = content_stripped[-1] if content_stripped else ''
            last_50_chars = content_stripped[-50:]
            last_words = last_50_chars.split()
            
            proper_endings = '.!?")\'」'
            if last_char not in proper_endings and not truncation_in_last_chars:
                if last_words:
                    last_word = last_words[-1]
                    if len(last_word) > 20:
                        return False, "Content appears truncated (ends with very long word)"
                    if len(last_word) > 10:
                        last_part = last_word[-5:].lower()
                        if len(last_part) >= 5 and not any(v in last_part for v in 'aeiou'):
                            return False, "Content appears truncated (ends with incomplete word)"
                
                if 200 <= len(content) <= 800:
                    sentences = re.split(r'[.!?]', content_stripped)
                    if sentences:
                        last_sentence = sentences[-1].strip()
                        if len(last_sentence) < 20 and last_char not in proper_endings:
                            return False, "Content appears truncated (ends with incomplete sentence)"
        
        # 6. Check for HTML/technical content
        html_patterns = ['<script', '<style', '<div', '<span', 'href=', 'src=', 'class=', 'id=', 'javascript:']
        html_count = sum(1 for pattern in html_patterns if pattern in content_lower)
        if html_count >= 3:
            return False, "Content appears to contain HTML/scraping artifacts"
        
        # 7. Check for suspiciously short content
        if len(content) < 100:
            if content_stripped and content_stripped[-1] not in '.!?")\'」':
                return False, "Content is too short and doesn't end properly (likely truncated)"
        
        # 8. Check AI summary quality
        if not ai_summary or len(ai_summary.strip()) < 50:
            return False, "AI summary is missing or too short"
        
        # Extract clean summary from JSON if wrapped
        clean_summary = ai_summary
        if ai_summary.strip().startswith('```json') or ai_summary.strip().startswith('{'):
            try:
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
                clean_summary = ai_summary
        
        if not clean_summary or len(clean_summary.strip()) < 50:
            return False, "AI summary is invalid or too short after JSON extraction"
        
        summary_lower = clean_summary.lower()
        error_summary_patterns = [
            'javascript error', 'error preventing access', 'browser error', 'page error',
            'loading error', 'scraping error', 'extraction error',
        ]
        
        summary_has_error = any(pattern in summary_lower for pattern in error_summary_patterns)
        if summary_has_error and error_count >= 1:
            return False, "Content and AI summary indicate error page/scraping failure"
        
        # 9. Check title quality
        if title:
            if len(title) > 500:
                return False, "Title is too long (might be content, not title)"
        
        # 10. Final check: Content should look like actual post content
        words = content_stripped.split()
        if len(words) < 10 and len(content) > 200:
            return False, "Content has too few words for its length (likely garbage data)"
        
        return True, None

    def _check_time_sensitive_keywords(self, content: str, ai_summary: str) -> bool:
        """Check if content contains time-sensitive keywords"""
        text = (content + ' ' + ai_summary).lower()
        
        high_confidence_patterns = [
            r'\bbreaking\b', r'\bbreaking news\b', r'\bjust in\b', r'\bdeveloping\b',
            r'\breleased this week\b', r'\bjust released\b', r'\bjust announced\b',
            r'\bannounced today\b', r'\blaunched today\b', r'\byesterday\b', r'\btoday\b',
            r'\btomorrow\b', r'\bthis morning\b', r'\bthis afternoon\b', r'\bthis evening\b',
            r'\bhours ago\b', r'\bdays ago\b', r'\bweeks ago\b', r'\bjust now\b',
            r'\burgent\b', r'\basap\b', r'\bimmediate\b', r'\bright now\b', r'\bcurrently\b',
            r'\bhappening now\b', r'\belection\b', r'\bvote\b', r'\bpoll\b', r'\bresults\b',
            r'\boutcome\b', r'\bdecision\b', r'\bverdict\b', r'\btrial\b', r'\bcourt\b',
            r'\bhearing\b', r'\blaunch\b.*\btoday\b', r'\brelease\b.*\btoday\b',
            r'\bunveiled\b.*\btoday\b', r'\bdebuted\b.*\btoday\b', r'\bintroduced\b.*\btoday\b',
            r'\bpremiered\b.*\btoday\b', r'\bmarket opens\b', r'\btrading\b.*\bnow\b',
            r'\bprice\b.*\b(crash|surge|rally)\b',
        ]
        
        for pattern in high_confidence_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        medium_confidence_patterns = [
            r'\bthis week\b', r'\bthis month\b', r'\brecently\b', r'\blastest\b',
        ]
        
        medium_count = sum(1 for pattern in medium_confidence_patterns if re.search(pattern, text, re.IGNORECASE))
        
        if medium_count >= 2:
            return True
        
        return False

    def _is_post_usable(self, post: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if post meets criteria for usable_posts.
        RELAXED CRITERIA: If post has analysis and passes quality checks, include it.
        """
        # Exclude DEPRECATED posts
        category = (post.get('category') or '').upper()
        if category == 'DEPRECATED':
            return False, None
        
        # Must have analysis scores (at least one > 0)
        rewrite_score = float(post.get('rewrite_score') or 0.0)
        value_score = float(post.get('value_score') or 0.0)
        quality_score = float(post.get('quality_score') or 0.0)
        
        # At least one score must be > 0 (post has some value)
        if rewrite_score <= 0 and value_score <= 0 and quality_score <= 0:
            return False, None
        
        # Must have ai_summary (minimum requirement)
        ai_summary = post.get('ai_summary') or ''
        if not ai_summary or len(ai_summary.strip()) < 30:
            return False, None
        
        # Analysis model is optional - if present, check it's valid, but don't require it
        analysis_model = post.get('analysis_model')
        if analysis_model and analysis_model not in ('gemini', 'mistral', 'ollama', 'qwen', 'qwen2.5:1.5b', 'qwen2.5:7b'):
            # Invalid model name - but don't exclude, just log
            logger.debug(f"Post {post.get('post_id')} has invalid analysis_model: {analysis_model}")
        
        relevance_window = post.get('relevance_window', 'evergreen')
        urgency_score = float(post.get('urgency_score') or 0.0)
        time_sensitive = bool(post.get('time_sensitive', False))
        created_at = post.get('created_at')
        
        # Check if commentary_worthy (manual override) - always include
        commentary_worthy = bool(post.get('commentary_worthy', False))
        if commentary_worthy:
            return True, 'commentary_worthy'
        
        # Check age
        age_info = None
        if created_at:
            try:
                if isinstance(created_at, str):
                    if 'T' in created_at:
                        created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        created_dt = datetime.fromisoformat(created_at)
                elif isinstance(created_at, datetime):
                    created_dt = created_at
                else:
                    created_dt = None
                
                if created_dt:
                    now = datetime.now(timezone.utc)
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
        
        # RELAXED CRITERIA: Include posts based on relevance_window and age
        
        # 1. Evergreen posts - include if < 6 months old (relaxed: no 1-week minimum)
        if relevance_window == 'evergreen':
            if age_info:
                # Exclude if too old (>= 6 months)
                if age_info['months'] >= 6.0:
                    return False, None
                # Include evergreen posts of any age < 6 months
                return True, 'evergreen'
            else:
                # No age info - include anyway (better to include than exclude)
                return True, 'evergreen'
        
        # 2. Time-sensitive posts - include if fresh (≤ 7 days)
        elif relevance_window in ('same-day', '24-72h', 'this-week'):
            if age_info:
                if age_info['days'] <= 7:
                    return True, 'fresh_time_sensitive'
                else:
                    # Older than 7 days - exclude
                    return False, None
            else:
                # No age info - assume fresh and include
                return True, 'fresh_time_sensitive'
        
        # 3. This-month posts - include if ≤ 30 days old
        elif relevance_window == 'this-month':
            if age_info:
                if age_info['days'] <= 30:
                    return True, 'time_sensitive_month'
                else:
                    return False, None
            else:
                # No age info - assume fresh and include
                return True, 'time_sensitive_month'
        
        # 4. Unknown relevance_window - include anyway (better to include than exclude)
        else:
            return True, 'unknown_relevance_window'

    def _parse_array_field(self, value: Any) -> Optional[List[str]]:
        """Parse array field from various formats to Python list or None"""
        if value is None:
            return None
        if isinstance(value, list):
            return value if value else None
        if isinstance(value, str):
            if not value or value.strip() == '' or value == '[]':
                return None
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed if parsed else None
                if isinstance(parsed, dict):
                    return None
            except:
                if ',' in value:
                    return [v.strip() for v in value.split(',') if v.strip()]
                return None
        return None

    def auto_curate_to_usable_posts(self, post: Dict[str, Any]) -> bool:
        """
        Automatically curate post to usable_posts table if it meets criteria.
        Called after post is saved and has analysis.
        
        Returns:
            True if post was added/updated in usable_posts, False otherwise
        """
        if not self._supabase:
            return False
        
        try:
            # 1. Check content quality
            content_valid, content_error = self._check_content_quality_for_curation(post)
            if not content_valid:
                logger.debug(f"Post {post.get('post_id')} excluded from usable_posts: {content_error}")
                # Remove from usable_posts if it was there before (quality degraded)
                self._remove_from_usable_posts(post.get('post_id'), post.get('platform'))
                return False
            
            # 2. Check if post is usable
            is_usable, inclusion_reason = self._is_post_usable(post)
            if not is_usable:
                logger.debug(f"Post {post.get('post_id')} excluded from usable_posts: not usable")
                # Remove from usable_posts if it was there before (no longer usable)
                self._remove_from_usable_posts(post.get('post_id'), post.get('platform'))
                return False
            
            # 3. Post is usable - insert/update in usable_posts
            try:
                # Parse JSON fields
                persona_fit_scores = post.get('persona_fit_scores')
                if isinstance(persona_fit_scores, str):
                    try:
                        persona_fit_scores = json.loads(persona_fit_scores)
                    except:
                        persona_fit_scores = {}
                
                persona_fit_reasons = post.get('persona_fit_reasons')
                if isinstance(persona_fit_reasons, str):
                    try:
                        persona_fit_reasons = json.loads(persona_fit_reasons)
                    except:
                        persona_fit_reasons = {}
                
                # Parse array fields
                tags = self._parse_array_field(post.get('tags'))
                key_concepts = self._parse_array_field(post.get('key_concepts'))
                rewrite_reasons = self._parse_array_field(post.get('rewrite_reasons'))
                rewrite_risks = self._parse_array_field(post.get('rewrite_risks'))
                best_persona_reasons = self._parse_array_field(post.get('best_persona_reasons'))
                fit_categories = self._parse_array_field(post.get('fit_categories'))
                
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
                    'inclusion_reason': inclusion_reason,
                    'commentary_worthy': bool(post.get('commentary_worthy', False)),
                }
                
                # Upsert to usable_posts (on conflict: platform,post_id)
                self._supabase.table('usable_posts').upsert(
                    data,
                    on_conflict='platform,post_id'
                ).execute()
                
                logger.info(f"✅ Auto-curated post {post.get('post_id')} to usable_posts ({inclusion_reason})")
                return True
                
            except Exception as e:
                logger.warning(f"Failed to insert post {post.get('post_id')} into usable_posts: {e}")
                return False
                
        except Exception as e:
            logger.debug(f"Auto-curation check failed for post {post.get('post_id')}: {e}")
            return False

    def _remove_from_usable_posts(self, post_id: Optional[str], platform: Optional[str]) -> None:
        """Remove post from usable_posts table if it no longer meets criteria"""
        if not self._supabase or not post_id or not platform:
            return
        
        try:
            self._supabase.table('usable_posts').delete().eq('post_id', post_id).eq('platform', platform).execute()
            logger.debug(f"Removed post {post_id} from usable_posts (no longer meets criteria)")
        except Exception as e:
            logger.debug(f"Failed to remove post {post_id} from usable_posts: {e}")

