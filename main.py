#!/usr/bin/env python3
"""
PrisMind - Social Media Content Collection and Analysis Platform

Main entry point for the PrisMind application.
Provides unified access to web interface, collection services, and CLI tools.
"""

import os
import sys
import argparse
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def run_web_app():
    """Launch the Streamlit web interface"""
    import subprocess
    
    app_path = Path(__file__).parent / "src" / "web" / "app.py"
    if not app_path.exists():
        print("❌ Web app not found at src/web/app.py")
        sys.exit(1)
    
    print("🚀 Starting PrisMind web interface...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        str(app_path), "--server.port=8501"
    ])

def run_collector():
    """Run the collection service"""
    try:
        from scripts.run_collector import main as collector_main
        print("🔄 Starting collection service...")
        collector_main()
    except ImportError as e:
        print(f"❌ Could not import collector: {e}")
        sys.exit(1)

def run_dashboard():
    """Launch the dashboard"""
    try:
        from scripts.dashboard import main as dashboard_main
        print("📊 Starting dashboard...")
        dashboard_main()
    except ImportError as e:
        print(f"❌ Could not import dashboard: {e}")
        sys.exit(1)

def setup_environment():
    """Check and setup environment"""
    env_file = Path(__file__).parent / ".env"
    env_example = Path(__file__).parent / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        print("⚠️ No .env file found. Please copy .env.example to .env and configure your settings.")
        return False
    
    return True

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="PrisMind - Social Media Content Collection and Analysis Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py web              # Launch web interface (default)
  python main.py collect          # Run collection service
  python main.py dashboard        # Launch dashboard
  python main.py --help           # Show this help message
        """
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        default="web",
        choices=["web", "collect", "dashboard"],
        help="Command to run (default: web)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="PrisMind 1.0.0"
    )
    
    args = parser.parse_args()
    
    # Setup environment
    if not setup_environment():
        sys.exit(1)
    
    # Route to appropriate function
    if args.command == "web":
        run_web_app()
    elif args.command == "collect":
        run_collector()
    elif args.command == "dashboard":
        run_dashboard()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()