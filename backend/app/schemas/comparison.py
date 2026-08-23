import uuid

from pydantic import BaseModel


class ComparisonSide(BaseModel):
    user_id: uuid.UUID
    rounds_played: int
    best_score_to_par: int | None
    average_score_to_par: float | None


class HoleComparison(BaseModel):
    hole_id: uuid.UUID
    hole_number: int
    par: int
    my_average: float | None
    friend_average: float | None
    result: str


class ComparisonResponse(BaseModel):
    layout_id: uuid.UUID
    me: ComparisonSide
    friend: ComparisonSide
    holes: list[HoleComparison]
