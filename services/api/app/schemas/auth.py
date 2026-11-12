from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 12


def validate_password_strength(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    if len(value) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password must be at most {PASSWORD_MAX_LENGTH} characters")
    groups = (
        any(char.islower() for char in value),
        any(char.isupper() for char in value),
        any(char.isdigit() for char in value),
        any(not char.isalnum() for char in value),
    )
    if sum(groups) < 3:
        raise ValueError("Password must include at least three character classes")
    return value


class PasswordRequest(BaseModel):
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        return validate_password_strength(value)


class RegisterRequest(PasswordRequest):
    email: EmailStr
    client: Literal["web", "mobile"] = "web"
    device_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    # Keep login compatible with accounts created under the previous policy;
    # the 8–12 character rule applies when setting a password.
    password: str = Field(min_length=1, max_length=1024)
    client: Literal["web", "mobile"] = "web"
    device_name: str | None = Field(default=None, max_length=100)


class EmailActionRequest(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)


class ResetPasswordRequest(PasswordRequest):
    token: str = Field(min_length=20, max_length=256)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: UUID
    email: EmailStr
    email_verified: bool
    is_active: bool
    created_at: datetime


class AuthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: UserResponse
    access_token: str | None = None
    token_type: str | None = None
    csrf_token: str | None = None
    expires_at: datetime
    session_token: str | None = Field(default=None, exclude=True, repr=False)


class RegistrationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: UserResponse
    message: str


class AuthMessageResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str


class SessionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    device_name: str | None
    user_agent: str | None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool


class CsrfResponse(BaseModel):
    csrf_token: str
