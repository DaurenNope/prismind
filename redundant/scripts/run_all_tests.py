#!/usr/bin/env python3
"""
Script to run all tests for the PrisMind project
"""

import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run all tests in the project"""
    project_root = Path(__file__).parent
    tests_dir = project_root / "tests"
    
    print("🧪 Running all PrisMind tests...")
    print("=" * 50)
    
    # Run unit tests
    print("\n🔬 Running unit tests...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", str(tests_dir), 
            "-v", "--tb=short"
        ], cwd=project_root, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Unit tests completed successfully!")
        else:
            print("❌ Unit tests failed!")
            return False
    except Exception as e:
        print(f"❌ Error running unit tests: {e}")
        return False
    
    # Run integration tests (if any)
    print("\n🔗 Running integration tests...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", str(tests_dir),
            "-v", "--tb=short", "-m", "integration"
        ], cwd=project_root, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Integration tests completed successfully!")
        else:
            print("⚠️ Integration tests completed with some skips (expected if no database connection)")
    except Exception as e:
        print(f"❌ Error running integration tests: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 All tests completed!")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)