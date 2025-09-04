#!/usr/bin/env python3
"""
🚀 PrisMind Auto-Deployment Script
================================

This script automates everything possible for deployment:
- Validates your environment and API keys
- Creates deployment configuration files
- Opens deployment links automatically
- Generates ready-to-paste secrets configuration

Just run: python deploy.py
"""

import os
import webbrowser
import subprocess

def print_banner():
    print("""
🧠 ═══════════════════════════════════════════════════════════
    PrisMind Auto-Deployment Script
    🚀 Automated Intelligence Platform Deployment
═══════════════════════════════════════════════════════════
""")

def check_api_keys():
    """Check which API keys are configured"""
    print("🔍 Checking API Keys Configuration...")
    
    keys = {
        "MISTRAL_API_KEY": os.getenv('MISTRAL_API_KEY'),
        "GEMINI_API_KEY": os.getenv('GEMINI_API_KEY'),
        "REDDIT_CLIENT_ID": os.getenv('REDDIT_CLIENT_ID'),
        "REDDIT_CLIENT_SECRET": os.getenv('REDDIT_CLIENT_SECRET'),
        "REDDIT_USERNAME": os.getenv('REDDIT_USERNAME'),
        "REDDIT_PASSWORD": os.getenv('REDDIT_PASSWORD'),
        "TWITTER_USERNAME": os.getenv('TWITTER_USERNAME'),
        "THREADS_USERNAME": os.getenv('THREADS_USERNAME'),
    }
    
    configured_keys = []
    missing_keys = []
    
    for key, value in keys.items():
        if value:
            configured_keys.append(key)
            print(f"✅ {key}: Configured")
        else:
            missing_keys.append(key)
            print(f"❌ {key}: Missing")
    
    return configured_keys, missing_keys

def generate_secrets_toml(configured_keys):
    """Generate TOML configuration for Streamlit secrets"""
    print("\n📝 Generating Streamlit Secrets Configuration...")
    
    secrets_content = "[secrets]\n"
    secrets_content += '# Add your Supabase credentials here:\n'
    secrets_content += 'SUPABASE_URL = "https://your-project.supabase.co"\n'
    secrets_content += 'SUPABASE_SERVICE_ROLE_KEY = "your_service_role_key_here"\n\n'
    
    # Add configured API keys
    for key in configured_keys:
        value = os.getenv(key)
        if value:
            secrets_content += f'{key} = "{value}"\n'
    
    # Add placeholders for missing keys
    missing_keys = [
        "MISTRAL_API_KEY", "GEMINI_API_KEY", "REDDIT_CLIENT_ID", 
        "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD",
        "TWITTER_USERNAME", "THREADS_USERNAME"
    ]
    
    for key in missing_keys:
        if key not in configured_keys:
            secrets_content += f'{key} = "your_{key.lower()}_here"\n'
    
    # Save to file for easy copying
    with open("streamlit_secrets.toml", "w") as f:
        f.write(secrets_content)
    
    print("✅ Secrets configuration saved to: streamlit_secrets.toml")
    return secrets_content

def check_git_status():
    """Check if code is pushed to GitHub"""
    print("\n📡 Checking GitHub Status...")
    
    try:
        # Get remote URL
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, cwd="."
        )
        
        if result.returncode == 0:
            repo_url = result.stdout.strip()
            print(f"✅ GitHub Repository: {repo_url}")
            
            # Check if there are unpushed commits
            result = subprocess.run(
                ["git", "status", "--porcelain", "--branch"],
                capture_output=True, text=True, cwd="."
            )
            
            if "ahead" in result.stdout:
                print("⚠️  Warning: You have unpushed commits")
                push = input("🤔 Push to GitHub now? (y/n): ")
                if push.lower() == 'y':
                    subprocess.run(["git", "push", "origin", "main"], cwd=".")
                    print("✅ Code pushed to GitHub!")
            else:
                print("✅ Code is up to date on GitHub")
                
            return repo_url
        else:
            print("❌ No GitHub repository found")
            return None
            
    except Exception as e:
        print(f"❌ Git check failed: {e}")
        return None

def open_deployment_links():
    """Open deployment websites automatically"""
    print("\n🌐 Opening Deployment Websites...")
    
    links = [
        ("Supabase Dashboard", "https://supabase.com/dashboard/projects"),
        ("Streamlit Cloud", "https://share.streamlit.io/"),
    ]
    
    for name, url in links:
        print(f"🔗 Opening {name}: {url}")
        webbrowser.open(url)

def create_deployment_guide():
    """Create a step-by-step deployment guide"""
    guide = """
🚀 PrisMind Deployment Guide
==========================

Your PrisMind is ready for deployment! Follow these steps:

STEP 1: Setup Supabase Database (2 minutes)
------------------------------------------
✅ Website opened automatically: https://supabase.com/dashboard/projects

1. Sign in with GitHub
2. Click "New Project"
3. Name: prismind  
4. Generate database password
5. Click "Create new project"
6. COPY THESE VALUES:
   - Project URL: https://xxxxx.supabase.co
   - Service role key: (Settings → API → service_role)

STEP 2: Deploy to Streamlit Cloud (2 minutes)  
--------------------------------------------
✅ Website opened automatically: https://share.streamlit.io/

1. Sign in with GitHub
2. Click "New app"
3. Repository: DaurenNope/prismind
4. Branch: main
5. Main file: app.py
6. Click "Advanced settings"
7. Copy-paste the content from streamlit_secrets.toml
   (Update the Supabase values from Step 1)
8. Click "Deploy!"

STEP 3: Your App is Live! 🎉
---------------------------
Your app will be available at:
https://prismind-[your-username].streamlit.app

Total Time: 4 minutes
Total Cost: $0 (100% FREE)

🧠 You now have a fully automated intelligence platform!
"""
    
    with open("DEPLOYMENT_GUIDE.md", "w") as f:
        f.write(guide)
    
    print("✅ Detailed guide saved to: DEPLOYMENT_GUIDE.md")
    return guide

def main():
    print_banner()
    
    # Check API keys
    configured_keys, missing_keys = check_api_keys()
    
    # Generate secrets configuration
    secrets_content = generate_secrets_toml(configured_keys)
    
    # Check Git status
    repo_url = check_git_status()
    
    if not repo_url:
        print("\n❌ Please push your code to GitHub first:")
        print("   git add . && git commit -m 'Deploy PrisMind' && git push origin main")
        return
    
    # Create deployment guide
    deployment_guide = create_deployment_guide()
    
    # Open deployment websites
    open_deployment_links()
    
    print("\n" + "="*60)
    print("🎯 READY FOR DEPLOYMENT!")
    print("="*60)
    
    if configured_keys:
        print(f"✅ {len(configured_keys)} API keys configured")
    
    if missing_keys:
        print(f"⚠️  {len(missing_keys)} API keys missing (you can add them later)")
    
    print("\n📋 NEXT STEPS:")
    print("1. Complete Supabase setup (website opened)")
    print("2. Deploy to Streamlit Cloud (website opened)")  
    print("3. Copy secrets from streamlit_secrets.toml")
    print("4. Your app will be live in 2 minutes!")
    
    print("\n📁 Files created for you:")
    print("   - streamlit_secrets.toml (ready to copy-paste)")
    print("   - DEPLOYMENT_GUIDE.md (step-by-step instructions)")
    
    print("\n🚀 Your PrisMind will be fully automated and FREE forever!")
    print("="*60)

if __name__ == "__main__":
    main()
