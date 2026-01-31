"""Users database operations."""

import logging
from typing import Any, Dict
from asgiref.sync import sync_to_async

from ninja import Router
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError

from core.models import Profile, Account
from core.utils.responses import success_response, error_response
from .schemas import UserRegistrationSchema, UserResponse

from features.auth.api import AuthBearer

logger = logging.getLogger(__name__)
router = Router()


# Fields to retrieve for user queries
USER_FIELDS = ("id", "first_name", "last_name", "email")
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
        "email": user_data.get("email"),
    }
    if profile_data:
        result.update(profile_data)
    return result


@router.get("/", response=UserResponse, auth=AuthBearer())
async def get_user(request):
    """Get user profile details."""
    user_id = request.user.id

    user_data = await User.objects.filter(id=user_id).values(*USER_FIELDS).afirst()
    if not user_data:
        return error_response("User not found", code=404)

    profile_data = await (
        Profile.objects.filter(user_id=user_id).values(*PROFILE_FIELDS).afirst()
    )
    return success_response(_format_user_response(user_data, profile_data))


@router.post("/", response=UserResponse)
async def create_user(request, payload: UserRegistrationSchema):
    """Register a new user with password."""

    # Complex transactional logic with multiple creates - keep in sync_to_async
    @sync_to_async
    def register_user():
        # Check for existing email
        if User.objects.filter(email=payload.email).exists():
            return None, "Email already registered"

        # Check for existing username
        if User.objects.filter(username=payload.username).exists():
            return None, "Username already taken"

        try:
            with transaction.atomic():
                # Create the Django User with hashed password
                user = User.objects.create_user(
                    username=payload.username,
                    email=payload.email,
                    password=payload.password,
                    first_name=payload.first_name,
                    last_name=payload.last_name,
                )

                # Create the Profile with optional fields
                Profile.objects.create(
                    user=user,
                    job_title=payload.job_title,
                    address=payload.address,
                    birthday=payload.birthday,
                    gender=payload.gender,
                    employment_status=payload.employment_status,
                    education_level=payload.education_level,
                )

                # Create default accounts
                Account.objects.create(
                    user=user,
                    name="Regular",
                    type="REGULAR",
                    balance=0.0,
                )
                Account.objects.create(
                    user=user,
                    name="Savings",
                    type="SAVINGS",
                    balance=0.0,
                )

            return {
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
            }, None

        except IntegrityError as e:
            logger.exception(f"Database integrity error during registration {e}")
            return None, "Registration failed: duplicate entry"
        except Exception as e:
            logger.exception("Failed to create user")
            return None, f"Failed to create user: {e}"

    result, error = await register_user()
    if error:
        return error_response(error, code=400)
    return success_response(result, "User registered successfully")
