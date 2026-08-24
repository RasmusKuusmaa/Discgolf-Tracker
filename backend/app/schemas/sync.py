import enum
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.course import CourseStatus, CourseVisibility
from app.models.friendship import FriendshipStatus
from app.models.round import RoundStatus
from app.schemas.geo import Coordinates


class SyncCourse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    city: str | None
    region: str | None
    country: str | None
    location: Coordinates
    created_by_id: uuid.UUID
    visibility: CourseVisibility
    status: CourseStatus
    osm_id: str | None
    is_verified: bool
    updated_at: datetime
    deleted: bool


class SyncLayout(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    name: str
    hole_count: int
    par_total: int
    total_distance_m: float | None
    difficulty: str | None
    is_default: bool
    is_active: bool
    updated_at: datetime
    deleted: bool


class SyncHole(BaseModel):
    id: uuid.UUID
    layout_id: uuid.UUID
    number: int
    par: int
    distance_m: float | None
    tee_location: Coordinates | None
    basket_location: Coordinates | None
    elevation_delta_m: float | None
    notes: str | None
    updated_at: datetime
    deleted: bool


class SyncRoundPlayer(BaseModel):
    id: uuid.UUID
    round_id: uuid.UUID
    user_id: uuid.UUID | None
    guest_name: str | None
    position: int
    is_scorekeeper: bool


class SyncRound(BaseModel):
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
    updated_at: datetime
    deleted: bool
    players: list[SyncRoundPlayer] = []


class SyncHoleScore(BaseModel):
    id: uuid.UUID
    round_id: uuid.UUID
    round_player_id: uuid.UUID
    hole_id: uuid.UUID
    strokes: int
    penalty_strokes: int
    is_circle_hit: bool | None
    is_fairway_hit: bool | None
    notes: str | None
    updated_at: datetime
    deleted: bool


class SyncFriendship(BaseModel):
    id: uuid.UUID
    requester_id: uuid.UUID
    addressee_id: uuid.UUID
    status: FriendshipStatus
    responded_at: datetime | None
    updated_at: datetime
    deleted: bool


class SyncUserAchievement(BaseModel):
    id: uuid.UUID
    achievement_id: uuid.UUID
    achievement_code: str
    unlocked_at: datetime | None
    progress: float
    updated_at: datetime
    deleted: bool


class SyncPullResponse(BaseModel):
    next_cursor: datetime
    has_more: bool = False
    courses: list[SyncCourse] = []
    layouts: list[SyncLayout] = []
    holes: list[SyncHole] = []
    rounds: list[SyncRound] = []
    scores: list[SyncHoleScore] = []
    friends: list[SyncFriendship] = []
    achievements: list[SyncUserAchievement] = []


class MutationEntityType(enum.StrEnum):
    COURSE = "course"
    LAYOUT = "layout"
    HOLE = "hole"
    ROUND = "round"
    ROUND_PLAYER = "round_player"
    HOLE_SCORE = "hole_score"


class MutationOp(enum.StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class ClientMutation(BaseModel):
    mutation_id: uuid.UUID
    entity_type: MutationEntityType
    op: MutationOp
    entity_id: uuid.UUID
    updated_at: datetime
    data: dict[str, object] = {}


class SyncPushRequest(BaseModel):
    mutations: list[ClientMutation] = Field(min_length=1)


class MutationResult(BaseModel):
    entity_type: MutationEntityType
    entity_id: uuid.UUID
    accepted: bool
    reason: str | None = None


class SyncPushResponse(BaseModel):
    results: list[MutationResult]


class CourseMutationData(BaseModel):
    name: str | None = None
    description: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    location: Coordinates | None = None
    visibility: CourseVisibility | None = None


class LayoutMutationData(BaseModel):
    course_id: uuid.UUID | None = None
    name: str | None = None
    difficulty: str | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class HoleMutationData(BaseModel):
    layout_id: uuid.UUID | None = None
    number: int | None = None
    par: int | None = None
    distance_m: float | None = None
    tee_location: Coordinates | None = None
    basket_location: Coordinates | None = None
    elevation_delta_m: float | None = None
    notes: str | None = None


class RoundMutationData(BaseModel):
    layout_id: uuid.UUID | None = None
    started_at: datetime | None = None
    is_practice: bool | None = None
    weather_note: str | None = None
    client_generated: bool | None = None


class RoundPlayerMutationData(BaseModel):
    round_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    guest_name: str | None = None
    position: int | None = None
    is_scorekeeper: bool | None = None


class HoleScoreMutationData(BaseModel):
    round_id: uuid.UUID | None = None
    round_player_id: uuid.UUID | None = None
    hole_id: uuid.UUID | None = None
    strokes: int | None = None
    penalty_strokes: int | None = None
    is_circle_hit: bool | None = None
    is_fairway_hit: bool | None = None
    notes: str | None = None
