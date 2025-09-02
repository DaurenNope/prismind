#!/usr/bin/env python3
"""
Setup Twitter Configuration - One-time setup for Twitter credentials
"""

import os
from pathlib import Path

def main():
    print("🔧 PrisMind Twitter Setup")
    print("=" * 40)
    
    project_root = Path(__file__).parent.absolute()
    config_dir = project_root / "config"
    config_dir.mkdir(exist_ok=True)
    
    print("This setup will help you configure Twitter access for PrisMind.")
    print("Your credentials will be stored locally and used for bookmark extraction.")
    print()
    
    # Get Twitter username
    username = input("📧 Enter your Twitter username (without @): ").strip()
    
    if not username:
        print("❌ Username is required!")
        return
    
    # Create .env file with username
    env_file = project_root / ".env"
    
    # Read existing .env if it exists
    env_content = ""
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.read()
    
    # Add or update TWITTER_USERNAME
    lines = env_content.split('\n')
    found_username = False
    
    for i, line in enumerate(lines):
        if line.startswith('TWITTER_USERNAME='):
            lines[i] = f'TWITTER_USERNAME={username}'
            found_username = True
            break
    
    if not found_username:
        lines.append(f'TWITTER_USERNAME={username}')
    
    # Write back to .env
    with open(env_file, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Configuration saved!")
    print(f"   📧 Username: {username}")
    print(f"   📁 Config dir: {config_dir}")
    print(f"   🔧 Environment: {env_file}")
    print()
    print("🎯 Next steps:")
    print("1. Run the dashboard: streamlit run scripts/dashboard_unified.py")
    print("2. Click '📥 Add NEW Bookmarks' to start collecting")
    print("3. First run will prompt for Twitter login in browser")
    print("4. Future runs will use saved session cookies")
    print()
    print("💡 The system will only collect SAVED posts (bookmarks), not liked posts")

if __name__ == "__main__":
    main()