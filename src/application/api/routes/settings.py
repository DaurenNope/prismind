from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.auth import require_api_key
from src.utils.logging_config import get_logger

try:
    from supabase import create_client  # type: ignore
except ImportError:  # pragma: no cover
    logger.error(f"Error: {e}")
    create_client = None  # type: ignore


logger = get_logger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


class PlatformCredentials(BaseModel):
    """Credentials payload for a platform."""

    platform: str
    username: Optional[str] = None
    password: Optional[str] = None
    cookie_file: Optional[str] = Field(default=None, alias="cookieFile")
    access_token: Optional[str] = Field(default=None, alias="accessToken")
    client_id: Optional[str] = Field(default=None, alias="clientId")
    client_secret: Optional[str] = Field(default=None, alias="clientSecret")
    user_agent: Optional[str] = Field(default=None, alias="userAgent")
    enabled: bool = True


def _make_supabase_client():
    """
    Create a Supabase client using service credentials.
    """
    if create_client is None:
        raise RuntimeError("supabase-py is not installed")

    import os

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials are missing")

    return create_client(url, key)


@router.get("/credentials")
async def get_credentials(user: str = Depends(require_api_key)) -> Dict[str, Any]:
    """
    Fetch stored platform credentials.
    
    Requires API authentication.
    """
    try:
        client = _make_supabase_client()
        response = client.table("platform_credentials").select("*").execute()
        data = getattr(response, "data", []) or []
        return {"platforms": data}
    except Exception as exc:
        logger.error(f"Failed to load credentials: {exc}")
        raise HTTPException(
            status_code=500, detail="Failed to load credentials"
        ) from exc


@router.post("/credentials")
async def upsert_credentials(
    payload: PlatformCredentials, user: str = Depends(require_api_key)
) -> Dict[str, Any]:
    """
    Upsert credentials for a platform.
    
    Requires API authentication.
    """
    try:
        client = _make_supabase_client()
        record = payload.model_dump(by_alias=True)
        record["platform"] = record["platform"].lower()
        response = (
            client.table("platform_credentials")
            .upsert(record, on_conflict="platform")
            .execute()
        )
        data = getattr(response, "data", []) or []
        return {
            "platform": record["platform"],
            "saved": True,
            "record": data[0] if data else record,
        }
    except Exception as exc:
        logger.error(f"Failed to upsert credentials for {payload.platform}: {exc}")
        raise HTTPException(
            status_code=500, detail=f"Failed to save credentials: {exc}"
        ) from exc
