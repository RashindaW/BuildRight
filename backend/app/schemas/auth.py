from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBase


class RegisterIn(BaseModel):
    model_config = {"extra": "forbid"}
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=255)


class LoginIn(BaseModel):
    model_config = {"extra": "forbid"}
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(ORMBase):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool


class CsrfOut(BaseModel):
    csrf_token: str
