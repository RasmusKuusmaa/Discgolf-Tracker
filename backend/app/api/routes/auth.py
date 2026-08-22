from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import create_token_pair, hash_password, hash_token
from app.db.session import get_session
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    existing = await session.execute(
        select(User).where((User.email == payload.email) | (User.username == payload.username))
    )
    if existing.scalar_one_or_none() is not None:
        raise AppError(
            "user_exists", "Email or username is already registered", status.HTTP_409_CONFLICT
        )

    user = User(
        email=payload.email,
        username=payload.username,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    await session.flush()

    pair = create_token_pair(user.id)
    session.add(
        RefreshToken(
            id=pair.refresh_token_id,
            token_hash=hash_token(pair.refresh_token),
            user_id=user.id,
            expires_at=pair.refresh_token_expires_at,
        )
    )
    await session.commit()

    return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)
