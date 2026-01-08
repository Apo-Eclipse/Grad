"""Users database operations."""

import logging
from typing import Any, Dict

from ninja import Router
from django.contrib.auth.models import User

from ..models import Profile
from ..core.responses import success_response, error_response
from .schemas import UserCreateSchema

logger = logging.getLogger(__name__)
router = Router()


def _user_to_dict(user: User, profile: Profile = None) -> Dict[str, Any]:
    """Convert User + Profile to dictionary matching expected API format."""
    result = {
        "user_id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }
    if profile:
        result.update(
            {
                "job_title": profile.job_title,
                "address": profile.address,
                "birthday": profile.birthday,
                "gender": profile.gender,
                "employment_status": profile.employment_status,
                "education_level": profile.education_level,
                "created_at": profile.created_at,
            }
        )
    return result


@router.get("/{user_id}", response=Dict[str, Any])
def get_user(request, user_id: int):
    """Get user profile details."""
    try:
        user = User.objects.get(id=user_id)
        try:
            profile = Profile.objects.get(user_id=user_id)
        except Profile.DoesNotExist:
            profile = None
        return _user_to_dict(user, profile)
    except User.DoesNotExist:
        return error_response("User not found", code=404)


@router.get("/{user_id}/exists", response=Dict[str, Any])
def check_user_exists(request, user_id: int):
    """Check if a user ID exists."""
    try:
        user = User.objects.get(id=user_id)
        return {
            "exists": True,
            "user": {
                "user_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
        }
    except User.DoesNotExist:
        return {"exists": False}


@router.post("/", response=Dict[str, Any])
def create_user(request, payload: UserCreateSchema):
    """Create a new user."""
    try:
        # Create the Django User - always auto-generate ID
        import uuid

        user = User.objects.create(
            first_name=payload.first_name,
            last_name=payload.last_name,
            username=f"user_{uuid.uuid4().hex[:8]}",  # Generate unique username
        )

        # Create the Profile
        profile = Profile.objects.create(
            user=user,
            job_title=payload.job_title,
            address=payload.address,
            birthday=payload.birthday,
            gender=payload.gender,
            employment_status=payload.employment_status,
            education_level=payload.education_level,
        )

        return success_response(
            {
                "user_id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "job_title": profile.job_title,
                "employment_status": profile.employment_status,
            },
            "User created successfully",
        )

    except Exception as e:
        logger.exception("Failed to create user")
        return error_response(f"Failed to create user: {e}")
