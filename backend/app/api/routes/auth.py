import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import create_token_pair, hash_password, hash_token, verify_password
from app.db.session import get_session
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_tokens(session: AsyncSession, user_id: uuid.UUID) -> TokenResponse:
    pair = create_token_pair(user_id)
    session.add(
        RefreshToken(
            id=pair.refresh_token_id,
            token_hash=hash_token(pair.refresh_token),
            user_id=user_id,
            expires_at=pair.refresh_token_expires_at,
        )
    )
    await session.commit()
    return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)


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

    return await _issue_tokens(session, user.id)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    result = await session.execute(
        select(User).where(
            (User.email == payload.identifier) | (User.username == payload.identifier)
        )
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError(
            "invalid_credentials",
            "Incorrect email/username or password",
            status.HTTP_401_UNAUTHORIZED,
        )
    if not user.is_active:
        raise AppError("account_disabled", "This account is disabled", status.HTTP_403_FORBIDDEN)

    return await _issue_tokens(session, user.id)
