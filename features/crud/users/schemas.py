from typing import Optional
from datetime import date, datetime

from ninja import Schema
from pydantic import validator

from core.models import EMPLOYMENT_OPTIONS, EDUCATION_OPTIONS, GENDER_OPTIONS


class UserSchema(Schema):
    id: int
    first_name: str
    last_name: str
    job_title: Optional[str] = None
    address: str
    birthday: date
    gender: str
    employment_status: str
    education_level: str
    created_at: datetime


class UserCreateSchema(Schema):
    first_name: str
    last_name: str
    job_title: Optional[str] = None
    address: str
    birthday: date
    gender: str
    employment_status: str
    education_level: str

    @validator("gender")
    def validate_gender(cls, v):
        if v not in GENDER_OPTIONS:
            raise ValueError(
                f"Invalid gender. Must be one of: {list(GENDER_OPTIONS.keys())}"
            )
        return v

    @validator("employment_status")
    def validate_employment_status(cls, v):
        if v not in EMPLOYMENT_OPTIONS:
            raise ValueError(
                f"Invalid employment_status. Must be one of: {list(EMPLOYMENT_OPTIONS.keys())}"
            )
        return v

    @validator("education_level")
    def validate_education_level(cls, v):
        if v not in EDUCATION_OPTIONS:
            raise ValueError(
                f"Invalid education_level. Must be one of: {list(EDUCATION_OPTIONS.keys())}"
            )
        return v
