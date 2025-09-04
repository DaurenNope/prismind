#!/usr/bin/env python3
"""
Database Analyzer - See what we have
"""

import sqlite3

def analyze_database():
    conn = sqlite3.connect('data/prismind.db')
    
    print("🔍 PRISMIND DATABASE ANALYSIS")
    print("=" * 50)
    
    # Get all tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f"\n📊 Total tables: {len(tables)}")
    
    # Analyze bookmark tables
    bookmark_tables = []
    for table in tables:
        if table[0].endswith('_bookmarks'):
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            bookmark_tables.append((table[0], count))
    
    print(f"\n📚 Bookmark tables: {len(bookmark_tables)}")
    
    # Sort by count
    bookmark_tables.sort(key=lambda x: x[1], reverse=True)
    
    print("\n📈 TOP CATEGORIES:")
    for table, count in bookmark_tables[:10]:
        if count > 0:
            category = table.replace('_bookmarks', '').replace('_', ' ').title()
            print(f"  {category}: {count} posts")
    
    print("\n🔧 DATABASE STRUCTURE:")
    for table, count in bookmark_tables:
        if count > 0:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            print(f"\n{table}:")
            print(f"  Posts: {count}")
            print(f"  Columns: {len(columns)}")
            for col in columns:
                print(f"    - {col[1]} ({col[2]})")
    
    # Sample data
    print("\n📄 SAMPLE POSTS:")
    for table, count in bookmark_tables[:3]:
        if count > 0:
            cursor.execute(f"SELECT content, value_score FROM {table} ORDER BY value_score DESC LIMIT 1")
            sample = cursor.fetchone()
            if sample:
                print(f"\n{table}:")
                print(f"  Best post: {sample[0][:100]}...")
                print(f"  Value score: {sample[1]}")
    
    conn.close()

if __name__ == "__main__":
    analyze_database()
