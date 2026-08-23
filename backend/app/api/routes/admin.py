from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.models.course_flag import CourseFlag
from app.models.user import User
from app.schemas.course_flag import CourseFlagListResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/flags", response_model=CourseFlagListResponse)
async def list_flags(
    limit: int = Query(default=50, ge=1, le=200),
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> CourseFlagListResponse:
    stmt = select(CourseFlag).order_by(CourseFlag.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return CourseFlagListResponse(items=list(result.scalars()))
