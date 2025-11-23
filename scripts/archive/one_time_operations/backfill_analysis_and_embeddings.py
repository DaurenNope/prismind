#!/usr/bin/env python3
"""
Backfill Analysis and Embeddings
=================================

Analyzes all posts in Supabase that don't have embeddings:
1. Fetches posts without embeddings
2. Runs AI analysis (if not already analyzed)
3. Generates embeddings
4. Updates Supabase with enriched data

Usage:
    python backfill_analysis_and_embeddings.py --limit 50
    python backfill_analysis_and_embeddings.py --all
"""

import asyncio
import argparse
from datetime import datetime
from src.infrastructure.database.manager import SupabaseManager
from src.domain.analysis.analyzers.intelligent_content_analyzer import IntelligentContentAnalyzer
from src.core.indexing.embedding_service import get_embedding_service


async def analyze_post(analyzer, post_data):
    """Analyze a single post"""
    try:
        analysis_content = {
            "post_id": post_data.get("post_id", ""),
            "title": post_data.get("title", ""),
            "content": post_data.get("content", ""),
            "url": post_data.get("url", ""),
            "platform": post_data.get("platform", ""),
            "author": post_data.get("author", ""),
            "author_handle": post_data.get("author_handle", ""),
            "created_at": post_data.get("created_at", datetime.now().isoformat()),
            "hashtags": post_data.get("hashtags", []),
        }
        
        result = await analyzer.analyze_content(analysis_content)
        return result
    except Exception as e:
        print(f"   ❌ Analysis failed: {e}")
        return {}


def generate_embedding(embedding_service, post_data):
    """Generate embedding for a post"""
    try:
        content_for_embedding = embedding_service.prepare_content_for_embedding(post_data)
        embedding = embedding_service.generate_embedding(content_for_embedding)
        return embedding
    except Exception as e:
        print(f"   ❌ Embedding generation failed: {e}")
        return None


async def backfill_posts(limit=None, skip_analysis=False):
    """Backfill analysis and embeddings for posts"""
    
    print("🚀 Starting backfill process...")
    print("=" * 70)
    
    # Initialize services
    sm = SupabaseManager()
    analyzer = IntelligentContentAnalyzer() if not skip_analysis else None
    embedding_service = get_embedding_service()
    
    if not embedding_service.is_available():
        print("❌ Embedding service not available!")
        print("   Install: pip install sentence-transformers")
        return
    
    # Fetch posts without embeddings
    query = sm.client.table('posts').select('*').is_('embedding', 'null')
    
    if limit:
        query = query.limit(limit)
    
    result = query.execute()
    posts = result.data
    
    if not posts:
        print("✅ All posts already have embeddings!")
        return
    
    print(f"📊 Found {len(posts)} posts to process")
    print()
    
    success_count = 0
    error_count = 0
    
    for i, post in enumerate(posts, 1):
        post_id = post.get('post_id', 'unknown')
        title = (post.get('title') or post.get('content', ''))[:50]
        
        print(f"[{i}/{len(posts)}] Processing: {post_id}")
        print(f"   Title: {title}...")
        
        update_data = {}
        
        # Step 1: Analyze if not already analyzed
        needs_analysis = not post.get('analyzed_at') and not skip_analysis
        if needs_analysis and analyzer:
            print(f"   🧠 Analyzing with AI...")
            analysis_result = await analyze_post(analyzer, post)
            
            if analysis_result:
                # Extract key fields for Supabase (filter out unsupported ones)
                supported_fields = [
                    'category', 'subcategory', 'content_type', 'summary',
                    'sentiment', 'value_score', 'content_quality_score',
                    'key_concepts', 'tags', 'analyzed_at'
                ]
                
                for field in supported_fields:
                    if field in analysis_result:
                        update_data[field] = analysis_result[field]
                
                # Set analysis metadata
                update_data['analyzed_at'] = datetime.now().isoformat()
                if 'ai_service' in analysis_result:
                    update_data['analysis_model'] = analysis_result['ai_service']
                
                print(f"   ✅ Analysis complete: {update_data.get('category', 'N/A')}")
        
        # Step 2: Generate embedding
        print(f"   🔢 Generating embedding...")
        
        # Merge post data with analysis for embedding
        enriched_post = {**post, **update_data}
        embedding = generate_embedding(embedding_service, enriched_post)
        
        if embedding:
            update_data['embedding'] = embedding
            update_data['embedding_model'] = embedding_service.model_name
            print(f"   ✅ Embedding generated ({len(embedding)} dims)")
        else:
            print(f"   ⚠️  Embedding generation failed")
        
        # Step 3: Update Supabase
        if update_data:
            try:
                sm.client.table('posts').update(update_data).eq('post_id', post_id).execute()
                success_count += 1
                print(f"   ✅ Updated in Supabase")
            except Exception as e:
                error_count += 1
                print(f"   ❌ Update failed: {e}")
        
        print()
        
        # Rate limiting
        if i % 10 == 0:
            print(f"💤 Processed {i} posts, taking a short break...")
            await asyncio.sleep(2)
    
    print("=" * 70)
    print(f"🎉 Backfill complete!")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📊 Total: {len(posts)}")


def main():
    parser = argparse.ArgumentParser(description='Backfill analysis and embeddings for posts')
    parser.add_argument('--limit', type=int, help='Limit number of posts to process')
    parser.add_argument('--all', action='store_true', help='Process all posts without embeddings')
    parser.add_argument('--skip-analysis', action='store_true', help='Only generate embeddings, skip AI analysis')
    
    args = parser.parse_args()
    
    if args.all:
        limit = None
    elif args.limit:
        limit = args.limit
    else:
        # Default: process 10 posts
        limit = 10
        print(f"💡 Processing {limit} posts by default. Use --limit N or --all for more.")
        print()
    
    asyncio.run(backfill_posts(limit=limit, skip_analysis=args.skip_analysis))


if __name__ == '__main__':
    main()
