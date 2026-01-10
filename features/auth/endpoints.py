from ninja import Router
from django.contrib.auth import authenticate
from core.utils.responses import error_response
from .schemas import LoginSchema, TokenSchema
from .utils import create_token_pair

router = Router()


@router.post("/login", response=TokenSchema)
def login(request, payload: LoginSchema):
    """
    Authenticate user and return access/refresh tokens.
    """
    user = authenticate(username=payload.username, password=payload.password)
    if not user:
        return error_response("Invalid credentials", code=401)

    if not user.is_active:
        return error_response("User account is disabled", code=401)

    tokens = create_token_pair(user)
    return tokens
