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

        # Perform AI analysis
        log(f"Analyzing content with AI...")

        try:
            analysis_result = await analyzer.analyze_content(analysis_content)

            # Start with original post data
            enhanced_post = dict(post_dict)
            
            # Only add essential analysis fields - no more bloated columns!
            essential_fields = {
                'ai_summary': analysis_result.get('summary', ''),
                'value_score': analysis_result.get('value_score', 0.0),
                'quality_score': analysis_result.get('content_quality_score', analysis_result.get('quality_score', 0.0)),
                'sentiment': analysis_result.get('sentiment', ''),
                'key_concepts': analysis_result.get('key_concepts', []),
                'tags': analysis_result.get('tags', []),
                'category': analysis_result.get('category', '')
            }
            
            # Ensure list fields are actually lists
            for key in ("key_concepts", "tags"):
                val = essential_fields.get(key)
                if val is None:
                    essential_fields[key] = []
                elif not isinstance(val, list):
                    essential_fields[key] = [val] if val else []
            
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
            
            # Track which AI service was used for analysis
            if 'ai_service' in analysis_result:
                enhanced_post['analysis_model'] = analysis_result['ai_service']

        except Exception as analysis_error:
            log(f"AI analysis failed: {analysis_error}", "warning")
            enhanced_post = post_dict  # Use original data if analysis fails

        # Update post in local database instead of adding
        try:
            # Try to update the existing post with analysis data
            local_updated = db_manager.update_post(post_id, enhanced_post)
            if local_updated:
                log(f"Updated post in local database successfully", "success")
            else:
                # If update fails (post doesn't exist), try to add it
                local_stored = db_manager.add_post(enhanced_post)
                if local_stored:
                    log(f"Stored new post in local database successfully", "success")
                else:
                    log(f"Failed to store/update post in local database", "error")
                    return False
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
