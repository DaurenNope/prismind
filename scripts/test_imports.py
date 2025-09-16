#!/usr/bin/env python3
"""
Test script to verify imports are working correctly
"""
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all necessary imports work"""
    print("🧪 Testing imports...")
    
    try:
        from src.core.extraction import WorkingRedditExtractor
        print("✅ Successfully imported WorkingRedditExtractor")
        
        # Create an instance to verify it works
        extractor = WorkingRedditExtractor()
        print("✅ Successfully created WorkingRedditExtractor instance")
        
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)