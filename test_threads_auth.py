#!/usr/bin/env python3
import asyncio
import pytest

# Skip this entire test file while Threads is disabled
pytestmark = pytest.mark.skip(reason="Threads temporarily disabled (IP ban)")

from core.extraction.threads_extractor import ThreadsExtractor

async def test_threads_auth():
    """Test Threads authentication"""
    print("🔍 Testing Threads authentication...")
    
    extractor = ThreadsExtractor()
    
    try:
        # Try authentication
        auth_result = await extractor.authenticate(
            username="qronoya",
            password="",
            cookies_path="config/threads_cookies_qronoya.json"
        )
        
        print(f"✅ Authentication result: {auth_result}")
        
        if auth_result:
            print("🎉 Threads authentication successful!")
        else:
            print("❌ Threads authentication failed")
            
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
    finally:
        try:
            if hasattr(extractor, 'browser') and extractor.browser:
                await extractor.browser.close()
            if hasattr(extractor, 'pw') and extractor.pw:
                await extractor.pw.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_threads_auth())

