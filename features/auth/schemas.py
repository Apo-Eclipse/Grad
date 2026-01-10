from ninja import Schema


class LoginSchema(Schema):
    username: str
    password: str


class TokenSchema(Schema):
    access: str
    refresh: str
    user_id: int
    username: str
