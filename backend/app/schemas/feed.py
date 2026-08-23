import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.friendship import FriendSummary


class FeedRoundItem(BaseModel):
    round_id: uuid.UUID
    user: FriendSummary
    layout_id: uuid.UUID
    course_name: str
    completed_at: datetime
    score_to_par: int
    is_partial: bool


class FeedResponse(BaseModel):
    items: list[FeedRoundItem]
    next_cursor: str | None = None
