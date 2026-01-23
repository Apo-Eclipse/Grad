from typing import Optional
from datetime import date, datetime

from ninja import Schema
from pydantic import field_validator

from core.models import EMPLOYMENT_OPTIONS, EDUCATION_OPTIONS, GENDER_OPTIONS


class UserSchema(Schema):
    id: int
    first_name: str
    last_name: str
    email: str
    job_title: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    gender: Optional[str] = None
    employment_status: Optional[str] = None
    education_level: Optional[str] = None
    created_at: datetime


class UserRegistrationSchema(Schema):
    """Schema for user registration with password."""

    # Required User fields
    email: str
    username: str
    password: str
    first_name: str
    last_name: str

    # Optional Profile fields
    job_title: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    gender: Optional[str] = None
    employment_status: Optional[str] = None
    education_level: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        if v is not None and v not in GENDER_OPTIONS:
            raise ValueError(
                f"Invalid gender. Must be one of: {list(GENDER_OPTIONS.keys())}"
            )
        return v

    @field_validator("employment_status")
    @classmethod
    def validate_employment_status(cls, v):
        if v is not None and v not in EMPLOYMENT_OPTIONS:
            raise ValueError(
                f"Invalid employment_status. Must be one of: {list(EMPLOYMENT_OPTIONS.keys())}"
            )
        return v

    @field_validator("education_level")
    @classmethod
    def validate_education_level(cls, v):
        if v is not None and v not in EDUCATION_OPTIONS:
            raise ValueError(
                f"Invalid education_level. Must be one of: {list(EDUCATION_OPTIONS.keys())}"
            )
        return v


class UserOutSchema(Schema):
    user_id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    job_title: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    gender: Optional[str] = None
    employment_status: Optional[str] = None
    education_level: Optional[str] = None
    created_at: Optional[datetime] = None


class UserResponse(Schema):
    status: str
    message: str
    data: Optional[UserOutSchema] = None


# Keep for backwards compatibility if needed
UserCreateSchema = UserRegistrationSchema
