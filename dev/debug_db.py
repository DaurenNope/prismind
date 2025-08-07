#!/usr/bin/env python3

import sqlite3

def debug_database():
    """Debug the database connection and query"""
    
    try:
        conn = sqlite3.connect('data/prismind.db')
        cursor = conn.cursor()
        
        print("🔍 Testing database connection...")
        
        # Test 1: Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
        table_exists = cursor.fetchone()
        print(f"✅ Posts table exists: {table_exists is not None}")
        
        # Test 2: Check columns
        cursor.execute("PRAGMA table_info(posts)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        print(f"📋 Available columns: {column_names}")
        
        # Test 3: Test simple query
        cursor.execute("SELECT COUNT(*) FROM posts")
        count = cursor.fetchone()[0]
        print(f"📊 Total posts: {count}")
        
        # Test 4: Test the exact query that's failing
        try:
            cursor.execute("""
                SELECT id, post_id, platform, author, author_handle, content, 
                       summary, value_score, smart_tags, ai_summary, created_timestamp
                FROM posts 
                WHERE content IS NOT NULL AND content != ''
                LIMIT 1
            """)
            result = cursor.fetchone()
            print(f"✅ Query successful: {result is not None}")
            if result:
                print(f"📝 Sample post ID: {result[0]}")
        except Exception as e:
            print(f"❌ Query failed: {e}")
        
        # Test 5: Check if smart_tags column exists specifically
        if 'smart_tags' in column_names:
            print("✅ smart_tags column exists")
            # Test a query with smart_tags
            cursor.execute("SELECT smart_tags FROM posts LIMIT 1")
            smart_tags_result = cursor.fetchone()
            print(f"📝 Sample smart_tags: {smart_tags_result}")
        else:
            print("❌ smart_tags column does not exist")
            print("Available columns:", column_names)
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    debug_database() 