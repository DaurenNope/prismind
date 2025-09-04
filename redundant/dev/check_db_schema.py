#!/usr/bin/env python3

import sqlite3

def check_schema():
    conn = sqlite3.connect('data/prismind.db')
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("PRAGMA table_info(posts)")
    columns = cursor.fetchall()
    
    print("📋 Posts table schema:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # Get sample data
    cursor.execute("SELECT * FROM posts LIMIT 1")
    sample = cursor.fetchone()
    if sample:
        print("\n📝 Sample post data:")
        for i, col in enumerate(columns):
            print(f"  {col[1]}: {sample[i]}")
    
    # Check if smart_tags column exists
    column_names = [col[1] for col in columns]
    if 'smart_tags' in column_names:
        print("\n✅ smart_tags column exists")
    else:
        print("\n❌ smart_tags column does not exist")
        print("Available columns:", column_names)
    
    conn.close()

if __name__ == "__main__":
    check_schema() 