from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
import re
from app.models.user import UserRole

class UserRegister(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=150)
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    password: str = Field(..., min_length=1)
    confirm_password: Optional[str] = None
    role: Optional[UserRole] = UserRole.USER

    @field_validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty or blank")
        return v.strip()

    @field_validator('email')
    def email_valid(cls, v):
        if not v or not v.strip():
            raise ValueError("Email cannot be empty")
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v.strip().lower()

    @field_validator('username')
    def username_valid(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError("Username cannot be empty")
            if not re.match(r"^[a-zA-Z0-9_-]+$", v):
                raise ValueError("Username contains invalid characters (only alphanumeric, _, - allowed)")
        return v

class UserLogin(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime

Token.model_rebuild()
