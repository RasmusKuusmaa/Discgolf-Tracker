import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import Visibility


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    display_name: str
    avatar_url: str | None
    home_city: str | None
    country: str | None
    profile_visibility: Visibility
    stats_visibility: Visibility
    allow_friend_requests: bool
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    home_city: str | None = None
    profile_visibility: Visibility | None = None
    stats_visibility: Visibility | None = None
    allow_friend_requests: bool | None = None
