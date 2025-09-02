#!/usr/bin/env python3
"""
Simple AI Enhancement for All Bookmarks
Enhanced version that works with existing database structure
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scripts.database_manager import DatabaseManager
from core.analysis.thread_summarizer import ThreadSummarizer

def enhance_all_bookmarks_simple():
    """Enhance all bookmarks with AI analysis using existing infrastructure"""
    
    print("🧠 Starting simple AI enhancement of all bookmarks...")
    
    # Initialize components
    db_manager = DatabaseManager()
    thread_summarizer = ThreadSummarizer()
    
    # Get all posts
    df = db_manager.get_all_posts()
    total_posts = len(df)
    
    print(f"📊 Found {total_posts} total bookmarks")
    
    # Limit processing to prevent timeouts
    max_posts_to_process = 10  # Process only first 10 posts
    df = df.head(max_posts_to_process)
    total_posts = len(df)
    print(f"🔄 Processing first {total_posts} posts to prevent timeouts...")
    
    # Track progress
    enhanced_count = 0
    skipped_count = 0
    error_count = 0
    
    for index, row in df.iterrows():
        try:
            post_id = row.get('post_id')
            platform = row.get('platform', 'unknown')
            content = row.get('content', '')
            title = row.get('smart_title', '') or content[:100]
            
            print(f"\n🔄 Processing {index + 1}/{total_posts}: {platform} - {title[:60]}...")
            
            # Add timeout protection
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("AI analysis timed out")
            
            # Set 30-second timeout for each post
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)
            
            # Check if already enhanced (has good smart_title and smart_tags)
            current_smart_title = row.get('smart_title', '')
            current_smart_tags = row.get('smart_tags', '[]')
            
            # Skip if already well-enhanced (unless title is poor)
            is_well_enhanced = (
                current_smart_title and 
                len(current_smart_title.strip()) > 20 and
                not current_smart_title.startswith('🎯') and
                not current_smart_title.startswith('…') and
                not current_smart_title.startswith(':') and
                current_smart_tags != '[]'
            )
            
            if is_well_enhanced:
                print(f"   ✅ Already well-enhanced, skipping...")
                skipped_count += 1
                continue
            
            print(f"   🧠 Running AI analysis...")
            
            # Create a simple post object for the summarizer
            post_data = {
                'post_id': post_id,
                'platform': platform,
                'author': row.get('author', ''),
                'content': content,
                'url': row.get('url', ''),
                'created_at': row.get('created_at', ''),
                'engagement': row.get('engagement_score', 0)
            }
            
            # Generate summary and analysis
            try:
                summary_result = thread_summarizer.generate_summary_from_dict(post_data)
                print(f"      ✅ Summary generation complete")
                signal.alarm(0)  # Cancel timeout
            except TimeoutError:
                print(f"      ⏰ AI analysis timed out, skipping...")
                summary_result = {}
                error_count += 1
                continue
            except Exception as e:
                print(f"      ⚠️ Summary generation failed: {e}")
                summary_result = {}
                signal.alarm(0)  # Cancel timeout
            
            # Calculate an improved value score
            value_score = 5.0  # Default
            try:
                content_length = len(content)
                engagement = row.get('engagement_score', 0)
                
                # Content quality scoring
                if content_length > 200:
                    value_score += 0.5
                if content_length > 500:
                    value_score += 1.0
                if content_length > 1000:
                    value_score += 1.5
                
                # Engagement scoring
                if engagement > 50:
                    value_score += 0.5
                if engagement > 100:
                    value_score += 1.0
                if engagement > 500:
                    value_score += 1.5
                if engagement > 1000:
                    value_score += 2.0
                
                # Content type scoring
                if 'ai' in content.lower() or 'agent' in content.lower():
                    value_score += 0.5
                if 'tool' in content.lower() or 'platform' in content.lower():
                    value_score += 0.5
                if 'million' in content.lower() or 'revenue' in content.lower():
                    value_score += 1.0
                if 'tutorial' in content.lower() or 'guide' in content.lower():
                    value_score += 0.5
                
                # Media content bonus
                if 'pic.twitter.com' in content or 'video' in content.lower():
                    value_score += 0.5
                
                # Cap at 10
                value_score = min(value_score, 10.0)
                
            except:
                pass
            
            # Prepare update data - match database schema
            update_data = {
                'value_score': value_score,
                'category': summary_result.get('category', 'General'),
                'topic': summary_result.get('topic', ''),
                'summary': summary_result.get('summary', ''),
                'sentiment': summary_result.get('sentiment', 'neutral'),
                'key_concepts': json.dumps(summary_result.get('smart_tags', [])),
                'comment_analysis': None,
                'media_analysis': None,
                'intelligence_analysis': None
            }
            
            # Update database
            try:
                # Update analysis data
                db_manager.update_post_analysis(post_id, update_data)
                
                # Update smart fields separately
                smart_title = summary_result.get('smart_title', '')
                smart_tags = json.dumps(summary_result.get('smart_tags', []))
                db_manager.update_post_smart_fields(post_id, smart_title, smart_tags)
                
                enhanced_count += 1
                print(f"   ✅ Enhanced successfully!")
                print(f"      📝 Smart Title: {smart_title[:80] if smart_title else 'N/A'}...")
                print(f"      🏷️ Tags: {json.loads(smart_tags)[:3] if smart_tags else []}")
                print(f"      ⭐ Value Score: {value_score}/10")
            except Exception as e:
                print(f"      ❌ Database update failed: {e}")
                error_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"   ❌ Error processing post {post_id}: {e}")
            continue
    
    print(f"\n🎉 AI Enhancement Complete!")
    print(f"   📊 Total Posts: {total_posts}")
    print(f"   ✅ Enhanced: {enhanced_count}")
    print(f"   ⏭️ Skipped (already good): {skipped_count}")
    print(f"   ❌ Errors: {error_count}")
    if total_posts > 0:
        print(f"   🧠 AI Enhanced Ratio: {(enhanced_count + skipped_count)}/{total_posts} ({((enhanced_count + skipped_count)/total_posts*100):.1f}%)")
    else:
        print("   🧠 AI Enhanced Ratio: 0/0 (0.0%)")
    
    print(f"\n🔄 Refresh your dashboard to see the improvements!")

if __name__ == "__main__":
    enhance_all_bookmarks_simple()