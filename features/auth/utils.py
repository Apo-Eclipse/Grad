from typing import Dict
from ninja_jwt.tokens import RefreshToken
from django.contrib.auth.models import User


def create_token_pair(user: User) -> Dict[str, str]:
    """Generate access and refresh tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user_id": user.id,
        "username": user.username,
    }


def verify_active_user(user: User) -> bool:
    """Check if user is active."""
    return user.is_active
