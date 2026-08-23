import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.round import RoundStatus
from app.schemas.layout import LayoutRead


class RoundPlayerCreate(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    guest_name: str | None = Field(default=None, min_length=1, max_length=64)
    position: int = Field(ge=1)
    is_scorekeeper: bool = False

    @model_validator(mode="after")
    def _exactly_one_of_user_or_guest(self) -> Self:
        if (self.user_id is None) == (self.guest_name is None):
            raise ValueError("Exactly one of user_id or guest_name must be set")
        return self


class RoundCreate(BaseModel):
    id: uuid.UUID
    layout_id: uuid.UUID
    started_at: datetime | None = None
    is_practice: bool = False
    weather_note: str | None = None
    client_generated: bool = False
    players: list[RoundPlayerCreate] = Field(min_length=1)


class RoundPlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    guest_name: str | None
    position: int
    is_scorekeeper: bool


class RoundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    layout_id: uuid.UUID
    created_by_id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None
    status: RoundStatus
    is_practice: bool
    weather_note: str | None
    client_generated: bool
    is_partial: bool
    created_at: datetime
    players: list[RoundPlayerRead] = []


class RoundSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    layout_id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None
    status: RoundStatus
    is_practice: bool
    is_partial: bool


class RoundListResponse(BaseModel):
    items: list[RoundSummary]
    next_cursor: str | None = None


class RewardedAchievement(BaseModel):
    code: str
    name: str
    icon: str
    xp_reward: int


class RewardedPersonalBest(BaseModel):
    layout_id: uuid.UUID
    best_score_to_par: int


class RoundRewards(BaseModel):
    xp_gained: int
    level_up: bool
    new_level: int
    new_achievements: list[RewardedAchievement] = []
    new_personal_bests: list[RewardedPersonalBest] = []


class RoundCompleteResponse(RoundRead):
    rewards: RoundRewards


class ScorecardHoleScore(BaseModel):
    hole_id: uuid.UUID
    hole_number: int
    par: int
    strokes: int
    penalty_strokes: int
    diff_to_par: int
    running_total: int
    term: str
    is_circle_hit: bool | None
    is_fairway_hit: bool | None
    notes: str | None


class ScorecardPlayer(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    guest_name: str | None
    position: int
    is_scorekeeper: bool
    total_strokes: int
    total_penalties: int
    score_to_par: int
    scores: list[ScorecardHoleScore] = []


class RoundDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    layout_id: uuid.UUID
    created_by_id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None
    status: RoundStatus
    is_practice: bool
    weather_note: str | None
    client_generated: bool
    is_partial: bool
    created_at: datetime
    layout: LayoutRead
    players: list[ScorecardPlayer] = []
