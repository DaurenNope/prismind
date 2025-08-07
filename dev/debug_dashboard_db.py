#!/usr/bin/env python3

import sqlite3
import os

def debug_dashboard_database():
    """Debug which database the dashboard is actually using"""
    
    print("🔍 Debugging dashboard database connection...")
    
    # Check current working directory
    print(f"📁 Current working directory: {os.getcwd()}")
    
    # List all database files
    db_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.db'):
                db_files.append(os.path.join(root, file))
    
    print(f"📋 Found database files: {db_files}")
    
    # Test each database file
    for db_path in db_files:
        print(f"\n🔍 Testing database: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if posts table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                print(f"✅ Posts table exists in {db_path}")
                
                # Check columns
                cursor.execute("PRAGMA table_info(posts)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                print(f"📋 Columns in {db_path}: {column_names}")
                
                # Check if smart_tags column exists
                if 'smart_tags' in column_names:
                    print(f"✅ smart_tags column exists in {db_path}")
                    
                    # Test the exact query that's failing
                    try:
                        cursor.execute("""
                            SELECT id, post_id, platform, author, author_handle, content, 
                                   summary, value_score, smart_tags, ai_summary, created_timestamp
                            FROM posts 
                            WHERE content IS NOT NULL AND content != ''
                            LIMIT 1
                        """)
                        result = cursor.fetchone()
                        print(f"✅ Query successful in {db_path}: {result is not None}")
                        
                        # Get post count
                        cursor.execute("SELECT COUNT(*) FROM posts")
                        count = cursor.fetchone()[0]
                        print(f"📊 Total posts in {db_path}: {count}")
                        
                    except Exception as e:
                        print(f"❌ Query failed in {db_path}: {e}")
                else:
                    print(f"❌ smart_tags column does NOT exist in {db_path}")
                
            else:
                print(f"❌ Posts table does NOT exist in {db_path}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Error testing {db_path}: {e}")
    
    print("\n🎯 Summary:")
    print("The dashboard might be using a different database file than expected.")
    print("Check which database file has the smart_tags column.")

if __name__ == "__main__":
    debug_dashboard_database() 