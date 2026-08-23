import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.friendship import FriendSummary


class LeaderboardEntry(BaseModel):
    rank: int
    user: FriendSummary
    best_score_to_par: int
    achieved_at: datetime


class LeaderboardResponse(BaseModel):
    layout_id: uuid.UUID
    scope: str
    entries: list[LeaderboardEntry]
