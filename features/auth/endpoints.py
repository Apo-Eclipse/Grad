from ninja import Router
from django.contrib.auth import authenticate, get_user_model
from core.utils.responses import error_response
from .schemas import LoginSchema, TokenSchema
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
