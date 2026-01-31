from asgiref.sync import sync_to_async

from ninja import Router
from django.contrib.auth import authenticate, get_user_model
from core.utils.responses import error_response
from .schemas import LoginSchema, TokenSchema, RefreshSchema
from .utils import create_token_pair

router = Router()
User = get_user_model()


@router.post("/login", response=TokenSchema)
async def login(request, payload: LoginSchema):
    """
    Authenticate user with email and password, return access/refresh tokens.
    """
    # Get user by email using native async
    try:
        user_obj = await User.objects.aget(email=payload.email)
    except User.DoesNotExist:
        return error_response("Invalid credentials", code=401)

    # authenticate() is sync, must wrap
    @sync_to_async
    def do_authenticate():
        return authenticate(username=user_obj.username, password=payload.password)

    user = await do_authenticate()
    if not user:
        return error_response("Invalid credentials", code=401)

    if not user.is_active:
        return error_response("User account is disabled", code=401)

    # create_token_pair is sync, wrap it
    @sync_to_async
    def do_create_tokens():
        return create_token_pair(user)

    tokens = await do_create_tokens()
    return tokens


@router.post("/refresh", response=TokenSchema)
async def refresh_token(request, payload: RefreshSchema):
    """
    Refresh access token using a valid refresh token.
    """

    # Token operations involve JWT library which is sync
    @sync_to_async
    def refresh_access_token():
        from ninja_jwt.tokens import RefreshToken
        from ninja_jwt.exceptions import TokenError, InvalidToken

        try:
            refresh = RefreshToken(payload.refresh)

            # Check if user exists and is active
            user_id = refresh.payload.get("user_id")
            try:
                user = User.objects.get(id=user_id)
                if not user.is_active:
                    return None, "User account is disabled"
            except User.DoesNotExist:
                return None, "User not found"

            return {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user_id": user.id,
                "email": user.email,
            }, None

        except (TokenError, InvalidToken) as e:
            return None, f"Invalid refresh token: {str(e)}"
        except Exception:
            return None, "Token refresh failed"

    result, error = await refresh_access_token()
    if error:
        return error_response(
            error,
            code=401
            if "Invalid" in error or "disabled" in error or "not found" in error
            else 400,
        )
    return result
