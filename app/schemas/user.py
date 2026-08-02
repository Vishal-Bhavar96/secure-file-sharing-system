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
    has_avatar: bool = False
    theme_preference: str = "dark"
    default_file_sort: str = "date_desc"
    items_per_page: int = 10
    last_login_at: Optional[datetime] = None
    last_password_change_at: Optional[datetime] = None

class UserProfileUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty or blank")
        return v.strip()

class UserEmailChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_email: str = Field(..., min_length=3, max_length=150)
    confirm_new_email: str = Field(..., min_length=3, max_length=150)

    @field_validator('new_email', 'confirm_new_email')
    def validate_email_format(cls, v):
        if not v or not v.strip():
            raise ValueError("Email cannot be empty")
        email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v.strip().lower()

class UserPasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_new_password: str = Field(..., min_length=8, max_length=100)

class UserPreferencesUpdate(BaseModel):
    theme_preference: Optional[str] = "dark"
    default_file_sort: Optional[str] = "date_desc"
    items_per_page: Optional[int] = 10

class UserSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_activity_at: datetime
    is_current: bool = False

Token.model_rebuild()
