#!/usr/bin/env python3
"""
Fix duplicate detection in threads collector
"""

import re

# Read the file
with open('src/services/collection/platform_collectors.py', 'r') as f:
    content = f.read()

# Find the section to replace
old_pattern = r'''            # Check if post already exists
            if not force_recollect and (post_id in existing_ids or normalized_id in existing_ids or (existing_urls and url in existing_urls)):
                consecutive_seen += 1
                log(f"⏭️ Skipping duplicate (seen in DB): id={post_id} url={url}")
                continue
            
            # New post found → reset duplicate streak
            consecutive_seen = 0
            new_posts.append(post)'''

new_pattern = r'''            # Check for duplicates before scraping
            if not force_recollect and (post_id in existing_ids or normalized_id in existing_ids or (existing_urls and url in existing_urls)):
                consecutive_seen += 1
                log(f"⏭️ Skipping duplicate (seen in DB): id={post_id} url={url}")
                continue
            
            # New post found → reset duplicate streak
            consecutive_seen = 0
            new_posts.append(post)'''

# Replace the pattern
new_content = re.sub(old_pattern, new_pattern, content)

# Write back to file
with open('src/services/collection/platform_collectors.py', 'w') as f:
    f.write(new_content)

print("Fixed duplicate detection in threads collector")