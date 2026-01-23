from ninja import Schema


class LoginSchema(Schema):
    email: str
    password: str


class TokenSchema(Schema):
    access: str
    refresh: str
    user_id: int
    email: str


class RefreshSchema(Schema):
    refresh: str
