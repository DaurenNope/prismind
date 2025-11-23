"""
Profile Management API Routes
Handles CRUD operations for persona profiles
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/profiles", tags=["profiles"])

# Path to personas directory
PERSONAS_DIR = Path(__file__).resolve().parents[3] / "config" / "personas"


class ProfileCreateRequest(BaseModel):
    """Request model for creating a profile"""

    key: str = Field(..., description="Unique profile key (e.g., 'qronoya')")
    name: str = Field(..., description="Display name")
    handle: Optional[str] = Field(None, description="Social media handle")
    platform: str = Field("twitter", description="Primary platform")
    voice_description: str = Field(..., description="Voice description")
    expertise: List[str] = Field(
        default_factory=list, description="List of expertise areas"
    )
    platforms: List[str] = Field(
        default_factory=lambda: ["twitter", "threads"],
        description="Supported platforms",
    )
    filters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Content filters"
    )
    quality_thresholds: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Quality thresholds"
    )
    rewrite_preferences: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Rewrite preferences"
    )
    transformation_settings: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Transformation settings"
    )
    matching: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Matching configuration"
    )


class ProfileUpdateRequest(BaseModel):
    """Request model for updating a profile"""

    name: Optional[str] = None
    handle: Optional[str] = None
    platform: Optional[str] = None
    voice_description: Optional[str] = None
    expertise: Optional[List[str]] = None
    platforms: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None
    quality_thresholds: Optional[Dict[str, Any]] = None
    rewrite_preferences: Optional[Dict[str, Any]] = None
    transformation_settings: Optional[Dict[str, Any]] = None
    matching: Optional[Dict[str, Any]] = None


def _get_profile_path(profile_key: str) -> Path:
    """Get the file path for a profile"""
    return PERSONAS_DIR / f"{profile_key}.json"


def _load_profile(profile_key: str) -> Dict[str, Any]:
    """Load a profile from file"""
    profile_path = _get_profile_path(profile_key)

    if not profile_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Profile '{profile_key}' not found"
        )

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Invalid JSON in profile file: {e}"
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading profile: {e}")


def _save_profile(profile_key: str, profile_data: Dict[str, Any]) -> None:
    """Save a profile to file"""
    profile_path = _get_profile_path(profile_key)

    # Ensure directory exists
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Ensure key is set
        profile_data["key"] = profile_key

        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving profile: {e}")


@router.get("")
async def list_profiles() -> Dict[str, Any]:
    """List all available profiles"""
    try:
        if not PERSONAS_DIR.exists():
            return {"profiles": [], "total": 0}

        profiles = []
        for profile_file in PERSONAS_DIR.glob("*.json"):
            # Skip example files
            if "example" in profile_file.name.lower():
                continue

            profile_key = profile_file.stem
            try:
                profile_data = _load_profile(profile_key)
                profiles.append(
                    {
                        "key": profile_key,
                        "name": profile_data.get("name", profile_key),
                        "handle": profile_data.get("handle"),
                        "platform": profile_data.get("platform", "twitter"),
                        "expertise": profile_data.get("expertise", []),
                        "created_at": profile_data.get("created_at"),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to load profile {profile_key}: {e}")
                continue

        return {"profiles": profiles, "total": len(profiles)}
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{profile_key}")
async def get_profile(profile_key: str) -> Dict[str, Any]:
    """Get a specific profile"""
    try:
        return _load_profile(profile_key)
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error getting profile {profile_key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_profile(request: ProfileCreateRequest) -> Dict[str, Any]:
    """Create a new profile"""
    try:
        profile_path = _get_profile_path(request.key)

        if profile_path.exists():
            raise HTTPException(
                status_code=409, detail=f"Profile '{request.key}' already exists"
            )

        # Build profile data
        profile_data = {
            "key": request.key,
            "name": request.name,
            "handle": request.handle,
            "platform": request.platform,
            "voice_description": request.voice_description,
            "expertise": request.expertise,
            "platforms": request.platforms,
            "filters": request.filters or {},
            "quality_thresholds": request.quality_thresholds or {},
            "rewrite_preferences": request.rewrite_preferences or {},
            "transformation_settings": request.transformation_settings or {},
            "matching": request.matching or {},
            "created_at": None,  # Will be set by system
        }

        _save_profile(request.key, profile_data)

        logger.info(f"Created profile: {request.key}")
        return {
            "success": True,
            "profile": profile_data,
            "message": f"Profile '{request.key}' created successfully",
        }
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{profile_key}")
async def update_profile(
    profile_key: str, request: ProfileUpdateRequest
) -> Dict[str, Any]:
    """Update an existing profile"""
    try:
        # Load existing profile
        profile_data = _load_profile(profile_key)

        # Update fields
        if request.name is not None:
            profile_data["name"] = request.name
        if request.handle is not None:
            profile_data["handle"] = request.handle
        if request.platform is not None:
            profile_data["platform"] = request.platform
        if request.voice_description is not None:
            profile_data["voice_description"] = request.voice_description
        if request.expertise is not None:
            profile_data["expertise"] = request.expertise
        if request.platforms is not None:
            profile_data["platforms"] = request.platforms
        if request.filters is not None:
            profile_data["filters"] = request.filters
        if request.quality_thresholds is not None:
            profile_data["quality_thresholds"] = request.quality_thresholds
        if request.rewrite_preferences is not None:
            profile_data["rewrite_preferences"] = request.rewrite_preferences
        if request.transformation_settings is not None:
            profile_data["transformation_settings"] = request.transformation_settings
        if request.matching is not None:
            profile_data["matching"] = request.matching

        # Ensure key is set
        profile_data["key"] = profile_key

        _save_profile(profile_key, profile_data)

        logger.info(f"Updated profile: {profile_key}")
        return {
            "success": True,
            "profile": profile_data,
            "message": f"Profile '{profile_key}' updated successfully",
        }
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{profile_key}")
async def delete_profile(profile_key: str) -> Dict[str, Any]:
    """Delete a profile"""
    try:
        profile_path = _get_profile_path(profile_key)

        if not profile_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Profile '{profile_key}' not found"
            )

        # Delete the file
        profile_path.unlink()

        logger.info(f"Deleted profile: {profile_key}")
        return {
            "success": True,
            "message": f"Profile '{profile_key}' deleted successfully",
        }
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{profile_key}/reload")
async def reload_profile(profile_key: str) -> Dict[str, Any]:
    """Reload a profile (useful after file changes)"""
    try:
        profile_data = _load_profile(profile_key)

        # Force PersonaMatcher to reload
        from src.domain.publishing.persona_matcher import get_persona_matcher

        matcher = get_persona_matcher()
        # Re-initialize to reload
        matcher.persona_profiles = matcher._load_personas()
        matcher._category_to_persona = matcher._build_category_mapping()

        return {
            "success": True,
            "message": f"Profile '{profile_key}' reloaded successfully",
            "profile": profile_data,
        }
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error reloading profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))
