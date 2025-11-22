#!/usr/bin/env python3
"""Generate AI summaries for posts that don't have them"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.new_database_manager import get_database_manager
import google.generativeai as genai


async def generate_summary(content: str, model) -> str:
    """Generate a clean, concise summary of the content"""
    
    if not content or len(content.strip()) < 20:
        return ""
    
    # Create a concise prompt
    prompt = f"""Summarize this social media post in 1-2 clear sentences. Focus on the main point and key takeaway. Be concise and engaging.

Post:
{content[:1000]}

Summary:"""
    
    try:
        response = model.generate_content(prompt)
        summary = response.text.strip() if response and response.text else ""
        return summary
    except Exception as e:
        print(f"Error: {e}")
        return ""


async def main():
    """Generate summaries for all posts without them"""
    
    print("🧠 Starting AI summary generation...")
    
    # Initialize Gemini
    gemini_key = os.getenv('GEMINI_API_KEY')
    if not gemini_key:
        print("❌ GEMINI_API_KEY not found!")
        return
    
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini initialized")
    
    db = get_database_manager()
    
    # Get posts without summaries
    posts = db.get_posts(limit=200)
    posts_to_process = [
        p for p in posts 
        if not p.get("ai_summary") and not p.get("content_summary")
        and p.get("content") and len(p.get("content", "")) > 20
    ]
    
    print(f"📊 Found {len(posts_to_process)} posts needing summaries")
    
    if not posts_to_process:
        print("✅ All posts already have summaries!")
        return
    
    # Process in small batches
    processed = 0
    errors = 0
    
    for post in posts_to_process[:30]:  # Limit to 30 to avoid rate limits
        try:
            post_id = post.get("id") or post.get("post_id")
            author = post.get("author", "Unknown")
            content = post.get("content", "")
            
            print(f"⏳ {author[:25]:25} ", end="", flush=True)
            
            # Generate summary
            summary = await generate_summary(content, model)
            
            if summary:
                # Update in database
                db.conn.execute(
                    "UPDATE posts SET ai_summary = ? WHERE id = ?",
                    (summary, post_id)
                )
                db.conn.commit()
                print(f"✅ {summary[:60]}...")
                processed += 1
            else:
                print(f"⚠️  Empty")
                errors += 1
                
        except Exception as e:
            print(f"❌ {str(e)[:40]}")
            errors += 1
        
        # Small delay to avoid rate limits
        await asyncio.sleep(2)
    
    print(f"\n" + "="*50)
    print(f"✅ Processed: {processed}")
    print(f"❌ Errors: {errors}")
    print(f"📊 Remaining: {len(posts_to_process) - 30}")


if __name__ == "__main__":
    asyncio.run(main())
