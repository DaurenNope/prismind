#!/usr/bin/env python3

import sqlite3
import subprocess
import json

def test_ai_analysis():
    """Test AI analysis on a real post from the database"""
    
    # Connect to database
    conn = sqlite3.connect('data/prismind.db')
    cursor = conn.cursor()
    
    # Get a post with content
    cursor.execute("""
        SELECT id, post_id, content, platform, author, author_handle
        FROM posts 
        WHERE content IS NOT NULL AND content != '' 
        ORDER BY id DESC 
        LIMIT 1
    """)
    
    post = cursor.fetchone()
    if not post:
        print("❌ No posts found in database")
        return
    
    post_id, db_post_id, content, platform, author, author_handle = post
    print(f"📝 Testing AI analysis on post {post_id}")
    print(f"Platform: {platform}")
    print(f"Author: {author} ({author_handle})")
    print(f"Content length: {len(content)} characters")
    print("-" * 50)
    
    # Create analysis prompt
    analysis_prompt = f"""
Analyze this social media post and provide a comprehensive summary:

POST DETAILS:
- Platform: {platform}
- Author: {author} ({author_handle})

CONTENT:
{content}

Please provide:
1. A concise summary (2-3 sentences)
2. Key insights or takeaways
3. Main topics discussed
4. Value score (1-10) and why
5. Suggested tags/categories

Format your response as JSON:
{{
    "summary": "brief summary",
    "key_insights": ["insight1", "insight2"],
    "topics": ["topic1", "topic2"],
    "value_score": 8,
    "value_reason": "why this score",
    "suggested_tags": ["tag1", "tag2"]
}}
"""
    
    print("🤖 Running AI analysis...")
    try:
        # Run Ollama analysis
        result = subprocess.run(
            ['ollama', 'run', 'qwen2.5:1.5b', analysis_prompt],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✅ AI Analysis Result:")
            print(result.stdout)
            
            # Try to parse JSON - look for JSON block in response
            response_text = result.stdout.strip()
            
            # Try to extract JSON from the response
            try:
                # Look for JSON block
                if '```json' in response_text:
                    json_start = response_text.find('```json') + 7
                    json_end = response_text.find('```', json_start)
                    if json_end != -1:
                        json_text = response_text[json_start:json_end].strip()
                        analysis = json.loads(json_text)
                    else:
                        analysis = json.loads(response_text)
                else:
                    analysis = json.loads(response_text)
                
                print("\n📊 Parsed Analysis:")
                print(f"Summary: {analysis.get('summary', 'N/A')}")
                print(f"Value Score: {analysis.get('value_score', 'N/A')}")
                print(f"Tags: {analysis.get('suggested_tags', [])}")
                print(f"Key Insights: {analysis.get('key_insights', [])}")
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Could not parse JSON: {e}")
                print("Raw response received successfully though!")
                
        else:
            print(f"❌ AI analysis failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ AI analysis timed out")
    except Exception as e:
        print(f"❌ Error running AI analysis: {e}")
    
    conn.close()

if __name__ == "__main__":
    test_ai_analysis() 