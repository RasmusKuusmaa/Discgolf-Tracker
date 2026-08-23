import uuid

from pydantic import BaseModel, ConfigDict, Field


class HoleScoreUpsert(BaseModel):
    id: uuid.UUID
    round_player_id: uuid.UUID
    hole_id: uuid.UUID
    strokes: int = Field(ge=1)
    penalty_strokes: int = Field(default=0, ge=0)
    is_circle_hit: bool | None = None
    is_fairway_hit: bool | None = None
    notes: str | None = None


class RoundScoresUpsert(BaseModel):
    scores: list[HoleScoreUpsert] = Field(min_length=1)


class HoleScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    round_player_id: uuid.UUID
    hole_id: uuid.UUID
    strokes: int
    penalty_strokes: int
    is_circle_hit: bool | None
    is_fairway_hit: bool | None
    notes: str | None


class RoundScoresResponse(BaseModel):
    scores: list[HoleScoreRead]
