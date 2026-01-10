"""Users database operations."""

import logging
from typing import Any, Dict

from ninja import Router
from django.contrib.auth.models import User

from core.models import Profile
from core.utils.responses import success_response, error_response
from .schemas import UserCreateSchema

from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router(auth=AuthBearer())


# Fields to retrieve for user queries
USER_FIELDS = ("id", "first_name", "last_name")
PROFILE_FIELDS = (
    "job_title",
    "address",
    "birthday",
    "gender",
    "employment_status",
    "education_level",
    "created_at",
)


def _format_user_response(
    user_data: Dict[str, Any], profile_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Format user + profile data for JSON response."""
    result = {
        "user_id": user_data["id"],
        "first_name": user_data["first_name"],
        "last_name": user_data["last_name"],
    }
    if profile_data:
        result.update(profile_data)
    return result


@router.get("/", response=Dict[str, Any])
def get_user(request):
    """Get user profile details."""
    user_id = request.user.id
    user_data = User.objects.filter(id=user_id).values(*USER_FIELDS).first()
    if not user_data:
        return error_response("User not found", code=404)

    profile_data = (
        Profile.objects.filter(user_id=user_id).values(*PROFILE_FIELDS).first()
    )
    return _format_user_response(user_data, profile_data)


@router.get("/{user_id}/exists", response=Dict[str, Any])
def check_user_exists(request, user_id: int):
    """Check if a user ID exists."""
    user_data = User.objects.filter(id=user_id).values(*USER_FIELDS).first()
    if user_data:
        return {
            "exists": True,
            "user": {
                "user_id": user_data["id"],
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
            },
        }
    return {"exists": False}


@router.post("/", response=Dict[str, Any], auth=None)
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
        Profile.objects.create(
            user=user,
            job_title=payload.job_title,
            address=payload.address,
            birthday=payload.birthday,
            gender=payload.gender,
            employment_status=payload.employment_status,
            education_level=payload.education_level,
        )

        # Return using values for consistency
        user_data = User.objects.filter(id=user.id).values(*USER_FIELDS).first()
        profile_data = (
            Profile.objects.filter(user_id=user.id)
            .values("job_title", "employment_status")
            .first()
        )

        return success_response(
            {
                "user_id": user_data["id"],
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "job_title": profile_data["job_title"] if profile_data else None,
                "employment_status": profile_data["employment_status"]
                if profile_data
                else None,
            },
            "User created successfully",
        )

    except Exception as e:
        logger.exception("Failed to create user")
        return error_response(f"Failed to create user: {e}")
