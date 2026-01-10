from ninja.security import HttpBearer
from ninja_jwt.authentication import JWTAuth
from typing import Optional, Any
from django.http import HttpRequest


class AuthBearer(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str) -> Optional[Any]:
        auth = JWTAuth()
        try:
            # ninja-jwt's JWTAuth.authenticate returns (user, token) or None
            # It usually expects the request object to have the header.
            # We are manually verifying the token string passed by Ninja's HttpBearer.

            # Using internal validation from ninja_jwt:
            validated_token = auth.get_validated_token(token)
            user = auth.get_user(validated_token)

            if user and user.is_active:
                request.user = user  # Set the user on the request
                return user
        except Exception:
            return None
        return None
