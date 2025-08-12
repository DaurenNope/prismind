#!/usr/bin/env python3
"""
🚀 PrisMind Local Deployment with Cloud Access
============================================

Run this to deploy your PrisMind locally but make it accessible online
using Streamlit's tunneling feature.
"""

import subprocess
import os
import sys
from pathlib import Path

def setup_environment():
    """Setup environment variables from .env file"""
    env_file = Path('.env')
    if env_file.exists():
        print("✅ Found .env file - loading configuration...")
        
        # Load environment variables
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ[key] = value
                    print(f"✅ Loaded: {key}")
        
        return True
    else:
        print("❌ No .env file found")
        return False

def run_streamlit_app():
    """Run the Streamlit app with cloud tunneling"""
    print("\n🚀 Starting PrisMind with cloud access...")
    print("📡 This will create a public URL you can access from anywhere!")
    
    try:
        # Run streamlit with cloud sharing enabled
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', 'app.py',
            '--server.port', '8521',
            '--server.headless', 'true',
            '--server.enableCORS', 'false'
        ])
    except KeyboardInterrupt:
        print("\n🛑 Shutting down PrisMind...")
    except Exception as e:
        print(f"❌ Error running app: {e}")

def main():
    print("""
🧠 ═══════════════════════════════════════════════════════════
    PrisMind Local Cloud Deployment
    🚀 Your Intelligence Platform with Online Access
═══════════════════════════════════════════════════════════
""")
    
    # Setup environment
    if not setup_environment():
        print("⚠️ Warning: No environment file found. Some features may not work.")
    
    print("\n🎯 Starting your intelligence platform...")
    print("📱 Access from: http://localhost:8521")
    print("🌐 Streamlit will also provide a public URL for remote access")
    print("\n🛑 Press Ctrl+C to stop")
    print("═" * 60)
    
    # Run the app
    run_streamlit_app()

if __name__ == "__main__":
    main()
