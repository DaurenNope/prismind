#!/usr/bin/env python3
"""
Auto-Collection Setup - Set up automated bookmark collection
"""

import os
import sys
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def setup_cron_job():
    """Set up a cron job for automated collection"""
    print("⚙️ Setting up automated bookmark collection...")
    print("=" * 50)
    
    # Create the collection script path
    collection_script = project_root / "collect_multi_platform.py"
    
    # Create a simple cron entry
    cron_command = f"0 */6 * * * cd {project_root} && source venv/bin/activate && python {collection_script} >> auto_collection.log 2>&1"
    
    print("📋 Automated Collection Setup Options:")
    print("1. Run every 6 hours")
    print("2. Run twice daily (8AM and 8PM)")
    print("3. Run daily at 9AM")
    print("4. Custom schedule")
    print("5. Show current auto-collection status")
    
    choice = input("\nChoose an option (1-5): ").strip()
    
    if choice == "1":
        schedule = "0 */6 * * *"  # Every 6 hours
        description = "every 6 hours"
    elif choice == "2":
        schedule = "0 8,20 * * *"  # 8AM and 8PM
        description = "twice daily (8AM and 8PM)"
    elif choice == "3":
        schedule = "0 9 * * *"  # 9AM daily
        description = "daily at 9AM"
    elif choice == "4":
        schedule = input("Enter cron schedule (e.g., '0 9 * * *'): ").strip()
        description = f"custom schedule: {schedule}"
    elif choice == "5":
        print("\n📊 Checking current auto-collection status...")
        os.system("crontab -l | grep collect_multi_platform || echo 'No auto-collection found'")
        return
    else:
        print("❌ Invalid choice")
        return
    
    full_cron = f"{schedule} cd {project_root} && source venv/bin/activate && python {collection_script} >> auto_collection.log 2>&1"
    
    print(f"\n⚙️ Setting up auto-collection to run {description}")
    print(f"📋 Cron job: {full_cron}")
    
    # Create a temporary cron file
    temp_cron = project_root / "temp_cron.txt"
    
    # Get existing cron jobs
    os.system(f"crontab -l > {temp_cron} 2>/dev/null || true")
    
    # Add new cron job (remove any existing ones first)
    with open(temp_cron, 'a') as f:
        f.write(f"\n# PrisMind Auto-Collection\n")
        f.write(f"{full_cron}\n")
    
    # Install the new cron
    result = os.system(f"crontab {temp_cron}")
    
    # Clean up
    temp_cron.unlink()
    
    if result == 0:
        print("✅ Auto-collection set up successfully!")
        print(f"📅 Will run {description}")
        print("📝 Logs will be saved to: auto_collection.log")
        print("\n💡 Commands:")
        print("   View logs: tail -f auto_collection.log")
        print("   Check cron: crontab -l")
        print("   Remove cron: crontab -e (then delete the PrisMind line)")
    else:
        print("❌ Failed to set up auto-collection")

def main():
    """Main setup function"""
    print("⚙️ PrisMind Auto-Collection Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not (project_root / "collect_multi_platform.py").exists():
        print("❌ Collection script not found!")
        print("Make sure you're running this from the PrisMind directory")
        return
    
    # Check virtual environment
    if not (project_root / "venv").exists():
        print("❌ Virtual environment not found!")
        print("Please set up the virtual environment first")
        return
    
    print("✅ Environment checks passed")
    
    setup_cron_job()

if __name__ == "__main__":
    main()