import uuid
from datetime import datetime

from pydantic import BaseModel


class ScoreDistribution(BaseModel):
    ace: int = 0
    eagle: int = 0
    birdie: int = 0
    par: int = 0
    bogey: int = 0
    double_bogey_or_worse: int = 0


class BestRound(BaseModel):
    round_id: uuid.UUID
    layout_id: uuid.UUID
    score_to_par: int
    completed_at: datetime


class StatsSummary(BaseModel):
    rounds_played: int
    courses_played: int
    layouts_played: int
    avg_score_to_par: float | None
    best_round: BestRound | None
    total_holes_played: int
    score_distribution: ScoreDistribution
