from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        requirements = {
            "at least 8 characters": len(password) >= 8,
            "at least one uppercase letter (A-Z)": any(
                "A" <= character <= "Z" for character in password
            ),
            "at least one lowercase letter (a-z)": any(
                "a" <= character <= "z" for character in password
            ),
            "at least one digit (0-9)": any(
                "0" <= character <= "9" for character in password
            ),
            "at least one special character": any(
                not character.isalnum() and not character.isspace()
                for character in password
            ),
            "no whitespace characters": not any(
                character.isspace() for character in password
            ),
        }
        missing = [
            requirement
            for requirement, satisfied in requirements.items()
            if not satisfied
        ]
        if missing:
            raise ValueError(f"Password must have {'; '.join(missing)}.")
        return password


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InternalUserOut(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
