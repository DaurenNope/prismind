#!/usr/bin/env python3
"""
Update Twitter post timestamps in the database to use the actual tweet timestamps
instead of the collection time.
"""
import os
import sqlite3
from datetime import datetime, timezone
import re

def main():
    # Path to the database
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'prismind.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all Twitter posts with their content
        cursor.execute("""
            SELECT id, post_id, content, created_at 
            FROM posts 
            WHERE platform = 'twitter' 
            ORDER BY created_at DESC
        """)
        
        updated_count = 0
        
        for row in cursor.fetchall():
            post_id, post_content, current_created_at = row[1], row[2], row[3]
            
            # Look for a timestamp in the content (common in tweet text)
            # Example: "3:45 PM · Sep 15, 2025" or "15:45 · 15 Sep 2025"
            timestamp_match = re.search(
                r'(\d{1,2}:\d{2}(?:\s*[AP]M)?[·\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{1,2}(?:[\s,]+\d{4})?)', 
                post_content
            )
            
            if timestamp_match:
                timestamp_str = timestamp_match.group(1)
                try:
                    # Try different date formats
                    for fmt in [
                        '%I:%M %p · %b %d, %Y',  # 3:45 PM · Sep 15, 2025
                        '%H:%M · %d %b %Y',       # 15:45 · 15 Sep 2025
                        '%I:%M%p · %b %d, %Y',    # 3:45PM · Sep 15, 2025
                        '%b %d, %Y'               # Sep 15, 2025
                    ]:
                        try:
                            # Parse the timestamp
                            dt = datetime.strptime(timestamp_str, fmt)
                            # Make it timezone-aware
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            
                            # Update the database
                            cursor.execute(
                                "UPDATE posts SET created_at = ? WHERE post_id = ?",
                                (dt.isoformat(), post_id)
                            )
                            updated_count += 1
                            print(f"✅ Updated {post_id} with timestamp {dt.isoformat()}")
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    print(f"⚠️ Error processing timestamp for {post_id}: {e}")
        
        # Commit changes
        conn.commit()
        print(f"\n✅ Updated {updated_count} Twitter posts with proper timestamps")
        
    except Exception as e:
        print(f"❌ Error updating timestamps: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
