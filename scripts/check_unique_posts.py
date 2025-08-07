#!/usr/bin/env python3
import sqlite3

def count_unique_posts():
    conn = sqlite3.connect('data/prismind.db')
    cursor = conn.cursor()
    
    # Get all bookmark tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_bookmarks'")
    tables = cursor.fetchall()
    
    all_post_ids = set()
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f'SELECT post_id FROM {table_name}')
        post_ids = cursor.fetchall()
        all_post_ids.update([pid[0] for pid in post_ids])
    
    print(f"Total unique posts across all tables: {len(all_post_ids)}")
    
    # Show breakdown by table
    for table in tables:
        table_name = table[0]
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        total = cursor.fetchone()[0]
        cursor.execute(f'SELECT COUNT(DISTINCT post_id) FROM {table_name}')
        unique = cursor.fetchone()[0]
        print(f"{table_name}: {total} total, {unique} unique")
    
    conn.close()

if __name__ == "__main__":
    count_unique_posts()
