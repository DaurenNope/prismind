#!/usr/bin/env python3
"""
Post Analysis and Storage Module
Handles AI analysis and database storage of collected posts
"""

import os
import json
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union, List
from pathlib import Path


# Load configuration
def load_collection_config():
    """Load collection configuration from config file"""
    config_path = Path("config/collection.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {"performance": {"skip_ai_analysis": False}}


# Analysis imports
from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer

# Optional local media analyzer
try:
    from src.core.analysis.local_media_analyzer import LocalMediaAnalyzer

    _LOCAL_MEDIA_AVAILABLE = True
except Exception:
    _LOCAL_MEDIA_AVAILABLE = False


def log(message: str, level: str = "info"):
    """Helper function for consistent logging"""
    prefix = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}.get(
        level, "ℹ️"
    )
    print(f"{prefix} {message}")


async def analyze_and_store_post(db_manager, post_dict, supabase_manager=None):
    """
    Analyze post with AI and store with analysis results.

    Args:
        db_manager: Database manager instance
        post_dict: Dictionary containing post data
        supabase_manager: Optional Supabase manager for cloud sync

    Returns:
        bool: True if successfully stored, False otherwise
    """
    # Global cancel check
    try:
        from src.services.cancel_manager import is_cancelled
        if is_cancelled("analysis"):
            log("Analysis cancelled by user", "warning")
            return False
    except Exception:
        pass

    post_id = post_dict.get("post_id", "unknown")
    log(f"Processing post: {post_id}")

    # Load configuration
    config = load_collection_config()
    skip_ai_analysis = config.get("performance", {}).get("skip_ai_analysis", False)
    
    # Check environment variable as well
    import os
    if os.environ.get("SKIP_AI_ANALYSIS", "").lower() in ("true", "1", "yes"):
        skip_ai_analysis = True

    # Determine if AI analysis should be performed
    if skip_ai_analysis:
        log(f"AI analysis skipped (performance mode)")
        enhanced_post = post_dict
        # Even if we skip analysis, we still want to store the post
        try:
            # Try to update first (in case it exists)
            local_updated = db_manager.update_post(post_id, enhanced_post)
            if not local_updated:
                # If update fails, try to add
                local_stored = db_manager.add_post(enhanced_post)
                if not local_stored:
                    log(f"Failed to store post in local database", "error")
                    return False
            log(f"Stored post in local database successfully (no AI analysis)", "success")
        except Exception as local_error:
            log(f"Local database operation failed: {local_error}", "error")
            return False
    else:
        # Create analyzer with enhanced configuration
        analyzer = IntelligentContentAnalyzer()

        # Prepare content for analysis
        analysis_content = {
            "post_id": post_dict.get("post_id", ""),
            "title": post_dict.get("title", ""),
            "content": post_dict.get("content", ""),
            "url": post_dict.get("url", ""),
            "platform": post_dict.get("platform", ""),
            "author": post_dict.get("author", ""),
            "author_handle": post_dict.get("username", ""),
            "created_at": post_dict.get("created_at", datetime.now().isoformat()),
            "hashtags": post_dict.get("hashtags", []),
            "engagement": post_dict.get("engagement", {}),
            "media_urls": post_dict.get("media_urls", []),
            "post_type": post_dict.get("post_type", "text")
        }

        # Threads-specific sanitization before analysis (fallback cleanup)
        try:
            if (post_dict.get('platform') == 'threads') and post_dict.get('content'):
                raw = str(post_dict.get('content') or '')
                import re
                text = raw
                # Remove 'Translate' artifacts
                text = re.sub(r"\bTranslate\b", " ", text)
                # Remove pagination markers like 1/3, 2 / 5
                text = re.sub(r"\b\d+\s*/\s*\d+\b", " ", text)
                # Remove short time markers like 1d, 2h, 15m
                text = re.sub(r"\b\d+\s*[dhm]\b", " ", text, flags=re.I)
                # Split and filter segments
                segs = re.split(r"[\n\r]+|\s{2,}", text)
                cleaned = []
                seen = set()
                for s in segs:
                    t = s.strip()
                    if not t:
                        continue
                    if len(t) < 6:
                        continue
                    if re.fullmatch(r"@[A-Za-z0-9._-]+", t):
                        continue
                    if re.fullmatch(r"[\w.-]+\.(com|net|org|io|ai)(/.*)?", t, re.I):
                        continue
                    key = re.sub(r"\s+", " ", t.lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    cleaned.append(t)
                cleaned_text = re.sub(r"\s+", " ", " ".join(cleaned)).strip()
                # If cleaned is reasonably better/longer or original looked truncated, replace
                looked_truncated = raw.rstrip().endswith(('...', '…')) or ('...' in raw) or ('…' in raw)
                if (len(cleaned_text) > max(len(raw), 150)) or looked_truncated:
                    post_dict['content'] = cleaned_text[:4000]
        except Exception:
            pass

        # Perform AI analysis
        log(f"Analyzing content with AI...")

        try:
            analysis_result = await analyzer.analyze_content(analysis_content)

            # Start with original post data
            enhanced_post = dict(post_dict)
            
            # Only add essential analysis fields - lean schema
            essential_fields = {
                'ai_summary': analysis_result.get('ai_summary') or analysis_result.get('summary', ''),
                'value_score': analysis_result.get('value_score', 0.0),
                'quality_score': analysis_result.get('quality_score', analysis_result.get('content_quality_score', 0.0)),
                'key_concepts': analysis_result.get('key_concepts', []),
                'tags': analysis_result.get('tags', []),
                'topic': analysis_result.get('topic', ''),
                'content_type': analysis_result.get('content_type', ''),
                'language': analysis_result.get('language', ''),
                'analyzed_at': analysis_result.get('analyzed_at'),
                'analysis_model': analysis_result.get('analysis_model') or analysis_result.get('ai_service'),
                # rewrite-focused
                'rewrite_score': analysis_result.get('rewrite_score'),
                'rewrite_readiness': analysis_result.get('rewrite_readiness'),
                'rewrite_reasons': analysis_result.get('rewrite_reasons'),
                'rewrite_risks': analysis_result.get('rewrite_risks'),
                'analysis_confidence': analysis_result.get('analysis_confidence'),
                'analysis_depth': analysis_result.get('analysis_depth'),
                'needs_deep_analysis': analysis_result.get('needs_deep_analysis'),
                # persona fit
                'persona_fit_scores': analysis_result.get('persona_fit_scores'),
                'persona_fit_reasons': analysis_result.get('persona_fit_reasons'),
                'best_persona_key': analysis_result.get('best_persona_key'),
                'best_persona_score': analysis_result.get('best_persona_score'),
                'best_persona_reasons': analysis_result.get('best_persona_reasons'),
                # time sensitivity
                'time_sensitive': analysis_result.get('time_sensitive'),
                'urgency_score': analysis_result.get('urgency_score'),
                'relevance_window': analysis_result.get('relevance_window'),
                'time_sensitive_reasons': analysis_result.get('time_sensitive_reasons'),
            }
            
            # Coerce defaults for completeness
            now_iso = datetime.now(timezone.utc).isoformat()
            if not essential_fields.get('analyzed_at'):
                essential_fields['analyzed_at'] = now_iso
            if not essential_fields.get('analysis_model'):
                essential_fields['analysis_model'] = 'analyzer-default'

            # Lightweight language fallback if model omitted
            if not essential_fields.get('language'):
                txt = (post_dict.get('content') or '')[:500]
                cyr = sum(1 for c in txt if '\u0400' <= c <= '\u04FF')
                lat = sum(1 for c in txt if c.isalpha() and ord(c) < 128)
                essential_fields['language'] = 'ru' if (cyr and cyr > 0.3 * (cyr + lat or 1)) else 'en'

            # content_type fallback from media presence
            if not essential_fields.get('content_type'):
                urls = post_dict.get('media_urls') or []
                if urls:
                    if any(str(u).lower().endswith(('.mp4', '.mov', '.webm')) for u in urls):
                        essential_fields['content_type'] = 'video'
                    elif any(str(u).lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')) for u in urls):
                        essential_fields['content_type'] = 'image'
                    else:
                        essential_fields['content_type'] = 'link'
                else:
                    essential_fields['content_type'] = 'text'

            # Ensure list fields are actually lists
            for key in ("key_concepts", "tags"):
                val = essential_fields.get(key)
                if val is None:
                    essential_fields[key] = []
                elif not isinstance(val, list):
                    essential_fields[key] = [val] if val else []
            
            # Media/content fallback to ensure non-empty content
            try:
                if not enhanced_post.get('content') or not str(enhanced_post.get('content')).strip():
                    fallback_pieces = []
                    # Prefer AI summary as a readable fallback
                    if essential_fields.get('ai_summary'):
                        fallback_pieces.append(str(essential_fields.get('ai_summary')))
                    # Use hashtags if present
                    ht = post_dict.get('hashtags') or []
                    if isinstance(ht, list) and ht:
                        fallback_pieces.append('#' + ' #'.join([str(h).strip('#') for h in ht[:8]]))
                    # Include author handle
                    ah = post_dict.get('author_handle') or post_dict.get('username')
                    if ah:
                        fallback_pieces.append(f"by @{str(ah).lstrip('@')}")
                    # Include URL as last resort
                    if post_dict.get('url'):
                        fallback_pieces.append(str(post_dict.get('url')))
                    fallback_text = ' \n'.join([p for p in fallback_pieces if p])
                    if fallback_text:
                        enhanced_post['content'] = fallback_text[:4000]
                    else:
                        enhanced_post['content'] = 'Content unavailable'
            except Exception:
                pass

            # Add only essential fields to the post
            enhanced_post.update(essential_fields)

            log(f"Analysis completed successfully", "success")
            
            # Generate embedding for semantic search
            try:
                from src.core.indexing.embedding_service import get_embedding_service
                
                embedding_service = get_embedding_service()
                if embedding_service.is_available():
                    # Prepare content (uses: content, title, hashtags, author)
                    content_for_embedding = embedding_service.prepare_content_for_embedding(enhanced_post)
                    
                    # Generate embedding vector
                    embedding = embedding_service.generate_embedding(content_for_embedding)
                    
                    if embedding:
                        enhanced_post['embedding'] = embedding
                        enhanced_post['embedding_model'] = embedding_service.model_name
                        log(f"Generated embedding ({len(embedding)} dims)", "success")
                    else:
                        log(f"Failed to generate embedding", "debug")
                else:
                    log("Embedding service not available", "debug")
            except Exception as embed_error:
                log(f"Embedding generation error: {embed_error}", "debug")
            
            # Ensure model marker
            if 'analysis_model' not in enhanced_post and 'ai_service' in analysis_result:
                enhanced_post['analysis_model'] = analysis_result['ai_service']

        except Exception as analysis_error:
            log(f"AI analysis failed: {analysis_error}", "warning")
            enhanced_post = post_dict  # Use original data if analysis fails

        # Update post in local database instead of adding
        try:
            # Try to update the existing post with analysis data
            local_updated = False
            try:
                if hasattr(db_manager, 'update_post'):
                    local_updated = bool(db_manager.update_post(post_id, enhanced_post))
            except Exception as e:
                log(f"Local update failed: {e}", "warning")
                local_updated = False

            if not local_updated:
                # If update did not apply (e.g., duplicate/ignored), try insert
                try:
                    local_stored = bool(db_manager.add_post(enhanced_post))
                except Exception as e:
                    log(f"Local insert failed: {e}", "warning")
                    local_stored = False

                if not local_stored:
                    # Final existence check: consider success if row already exists
                    try:
                        if hasattr(db_manager, 'get_post_by_id') and db_manager.get_post_by_id(post_id):
                            log("Post already existed; analysis update may have been a no-op", "info")
                        else:
                            log("Local store/update did not apply; proceeding anyway", "warning")
                    except Exception:
                        # If we cannot check existence, don't block pipeline
                        log("Could not verify local existence; proceeding", "warning")
            log(f"Local persistence complete", "success")
        except Exception as local_error:
            log(f"Local database operation failed: {local_error}", "error")
            return False

    # Store in Supabase if available
    if supabase_manager:
        try:
            log(
                f"Attempting Supabase sync for post: {enhanced_post.get('post_id', 'unknown')}"
            )
            cloud_result = supabase_manager.insert_post(enhanced_post)
            if cloud_result:
                log(
                    f"✅ Synced to Supabase successfully: {enhanced_post.get('post_id')}",
                    "success",
                )
            else:
                log(
                    f"❌ Supabase sync returned False for post: {enhanced_post.get('post_id')}",
                    "error",
                )
                log(f"Post data keys: {list(enhanced_post.keys())}", "error")
        except Exception as cloud_error:
            log(f"❌ Supabase sync exception: {cloud_error}", "error")
            log(
                f"Post data: {enhanced_post.get('post_id')} - {enhanced_post.get('url', 'no url')}",
                "error",
            )
            # Don't fail the whole operation if cloud sync fails
    else:
        log(f"⚠️ No Supabase manager available - skipping cloud sync", "warning")

    return True
