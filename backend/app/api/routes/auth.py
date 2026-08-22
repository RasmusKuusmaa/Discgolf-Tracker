import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.rate_limit import limiter
from app.core.security import (
    create_token_pair,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.session import get_session
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

AUTH_RATE_LIMIT = "10/minute"


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
@limiter.limit(AUTH_RATE_LIMIT)
async def register(
    request: Request, payload: RegisterRequest, session: AsyncSession = Depends(get_session)
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
@limiter.limit(AUTH_RATE_LIMIT)
async def login(
    request: Request, payload: LoginRequest, session: AsyncSession = Depends(get_session)
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


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(AUTH_RATE_LIMIT)
async def refresh(
    request: Request, payload: RefreshRequest, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token)
    except ValueError as exc:
        raise AppError(
            "invalid_token", "Refresh token is invalid or expired", status.HTTP_401_UNAUTHORIZED
        ) from exc
    if claims.get("type") != "refresh":
        raise AppError(
            "invalid_token", "Refresh token is invalid or expired", status.HTTP_401_UNAUTHORIZED
        )

    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token))
    )
    token_row = result.scalar_one_or_none()
    if token_row is None:
        raise AppError(
            "invalid_token", "Refresh token is invalid or expired", status.HTTP_401_UNAUTHORIZED
        )

    if token_row.revoked_at is not None:
        # This token was already rotated away — presenting it again means it
        # was stolen from an earlier point in the chain. Revoke every active
        # token for this user so the thief's session dies too.
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == token_row.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await session.commit()
        raise AppError(
            "token_reuse_detected",
            "Refresh token reuse detected; all sessions revoked",
            status.HTTP_401_UNAUTHORIZED,
        )

    if token_row.expires_at < datetime.now(UTC):
        raise AppError(
            "invalid_token", "Refresh token is invalid or expired", status.HTTP_401_UNAUTHORIZED
        )

    token_row.revoked_at = datetime.now(UTC)
    return await _issue_tokens(session, token_row.user_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(AUTH_RATE_LIMIT)
async def logout(
    request: Request, payload: RefreshRequest, session: AsyncSession = Depends(get_session)
) -> None:
    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token))
    )
    token_row = result.scalar_one_or_none()
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(UTC)
        await session.commit()
