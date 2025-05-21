from typing import Any, Optional, List
from datetime import datetime
from ninja import Schema
from pydantic import EmailStr, Field

from .models import User
from house_rental.schemas import MessageResponse

# User schemas
class GoogleAuthSchema(Schema):
    credential: str
    role: Optional[str] = None

class GoogleAuthResponseSchema(Schema):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[dict] = None
    user_exists: Optional[bool] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    google_id: Optional[str] = None
    picture: Optional[str] = None

class TwitterInitResponseSchema(Schema):
    oauth_token: str
    oauth_token_secret: str
    auth_url: str

class TwitterCallbackSchema(Schema):
    oauth_token: str
    oauth_verifier: str
    role: Optional[str] = None

class TwitterAuthResponseSchema(Schema):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    user: Optional[dict] = None
    user_exists: Optional[bool] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    twitter_id: Optional[str] = None
    picture: Optional[str] = None

class UserRegistrationSchema(Schema):
    username: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = User.Role.TENANT
    phone_number: Optional[str] = None

class UserLoginSchema(Schema):
    username: str  # Can be username or email
    password: str

class UserProfileSchema(Schema):
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    profile_picture: Optional[str] = None
    date_joined: Any

class UserProfileUpdateSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None

class PasswordChangeSchema(Schema):
    old_password: str
    new_password: str = Field(..., min_length=8)

# Admin schemas
class AdminUserListSchema(Schema):
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    is_active: bool
    date_joined: Any
    properties_count: int = 0
    bookings_count: int = 0

class PaginatedUserResponse(Schema):
    items: List[AdminUserListSchema]
    total: int
    page: int
    page_size: int
    total_pages: int