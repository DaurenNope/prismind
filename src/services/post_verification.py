"""
Post Verification Service
Verifies that posted content URLs are accessible and optionally verifies content matches
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


async def verify_post_url(post_url: str, timeout: int = 10) -> Dict[str, Any]:
    """Verify that a post URL is accessible"""
    if not post_url:
        return {
            "verified": False,
            "status_code": None,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "error": "No URL provided"
        }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                post_url,
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            
            return {
                "verified": response.status_code == 200,
                "status_code": response.status_code,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "error": None,
                "final_url": str(response.url) if response.url != post_url else None
            }
    except httpx.TimeoutException:
        return {
            "verified": False,
            "status_code": None,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "error": "Timeout",
            "final_url": None
        }
    except httpx.RequestError as e:
        return {
            "verified": False,
            "status_code": None,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "error": f"Request error: {str(e)}",
            "final_url": None
        }
    except Exception as e:
        logger.error(f"Error verifying post URL {post_url}: {e}", exc_info=True)
        return {
            "verified": False,
            "status_code": None,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "final_url": None
        }


async def verify_post_content(
    post_url: str,
    expected_content: str,
    timeout: int = 10
) -> Dict[str, Any]:
    """Verify post content matches expected (optional, platform-specific)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                post_url,
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            
            if response.status_code != 200:
                return {
                    "content_match": False,
                    "similarity": 0.0,
                    "expected_length": len(expected_content),
                    "actual_length": 0,
                    "error": f"HTTP {response.status_code}"
                }
            
            html = response.text
            
            # Simple content extraction (platform-specific logic would go here)
            # For now, just check if expected content appears in HTML
            content_lower = expected_content.lower()
            html_lower = html.lower()
            
            # Calculate simple similarity (percentage of expected content found)
            found_chars = sum(1 for char in content_lower if char in html_lower)
            similarity = found_chars / len(expected_content) if expected_content else 0.0
            
            return {
                "content_match": similarity > 0.8,
                "similarity": round(similarity, 2),
                "expected_length": len(expected_content),
                "actual_length": len(html),
                "error": None
            }
    except Exception as e:
        logger.error(f"Error verifying post content {post_url}: {e}", exc_info=True)
        return {
            "content_match": False,
            "similarity": 0.0,
            "expected_length": len(expected_content) if expected_content else 0,
            "actual_length": 0,
            "error": str(e)
        }


async def verify_post(
    post_url: str,
    expected_content: Optional[str] = None,
    verify_content: bool = False,
    timeout: int = 10
) -> Dict[str, Any]:
    """Complete post verification (URL + optional content)"""
    result = await verify_post_url(post_url, timeout)
    
    if verify_content and expected_content and result.get("verified"):
        content_result = await verify_post_content(post_url, expected_content, timeout)
        result["content"] = content_result
    
    return result

