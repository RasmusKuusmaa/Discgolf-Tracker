import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.friendship import FriendshipStatus


class FriendRequestCreate(BaseModel):
    username: str | None = None
    user_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _exactly_one_of_username_or_user_id(self) -> Self:
        if (self.username is None) == (self.user_id is None):
            raise ValueError("Exactly one of username or user_id must be set")
        return self


class FriendshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requester_id: uuid.UUID
    addressee_id: uuid.UUID
    status: FriendshipStatus
    created_at: datetime
    responded_at: datetime | None
