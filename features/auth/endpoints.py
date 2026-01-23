from ninja import Router
from django.contrib.auth import authenticate, get_user_model
from core.utils.responses import error_response
from .schemas import LoginSchema, TokenSchema, RefreshSchema
from .utils import create_token_pair

router = Router()
User = get_user_model()


@router.post("/login", response=TokenSchema)
def login(request, payload: LoginSchema):
    """
    Authenticate user with email and password, return access/refresh tokens.
    """
    try:
        user_obj = User.objects.get(email=payload.email)
    except User.DoesNotExist:
        return error_response("Invalid credentials", code=401)

    user = authenticate(username=user_obj.username, password=payload.password)
    if not user:
        return error_response("Invalid credentials", code=401)

    if not user.is_active:
        return error_response("User account is disabled", code=401)

    tokens = create_token_pair(user)
    return tokens


@router.post("/refresh", response=TokenSchema)
def refresh_token(request, payload: RefreshSchema):
    """
    Refresh access token using a valid refresh token.
    """
    from ninja_jwt.tokens import RefreshToken
    from ninja_jwt.exceptions import TokenError, InvalidToken

    try:
        refresh = RefreshToken(payload.refresh)

        # Check if user exists and is active
        user_id = refresh.payload.get("user_id")
        try:
            user = User.objects.get(id=user_id)
            if not user.is_active:
                return error_response("User account is disabled", code=401)
        except User.DoesNotExist:
            return error_response("User not found", code=401)

        # Generate new access token
        # refresh.access_token returns a new access token
        # We can also start a new refresh token if we want rotation, but for now
        # let's return the new access and the original (or rotated) refresh.

        # Validating the token automatically checks expiration.

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),  # Retrieve the token string
            "user_id": user.id,
            "email": user.email,
        }

    except (TokenError, InvalidToken) as e:
        return error_response(f"Invalid refresh token: {str(e)}", code=401)
    except Exception:
        return error_response("Token refresh failed", code=400)
