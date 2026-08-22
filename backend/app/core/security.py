import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import get_settings

_hasher = PasswordHasher()

JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    refresh_token_id: uuid.UUID
    refresh_token_expires_at: datetime


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.jwt_access_token_ttl_minutes)
    payload = {"sub": str(user_id), "type": "access", "iat": now, "exp": expires_at}
    return str(jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM))


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        claims: dict[str, Any] = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
        return claims
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def create_token_pair(user_id: uuid.UUID) -> TokenPair:
    settings = get_settings()
    access_token = create_access_token(user_id)

    refresh_token_id = uuid.uuid4()
    now = datetime.now(UTC)
    refresh_expires_at = now + timedelta(days=settings.jwt_refresh_token_ttl_days)
    refresh_payload = {
        "sub": str(user_id),
        "jti": str(refresh_token_id),
        "type": "refresh",
        "iat": now,
        "exp": refresh_expires_at,
    }
    refresh_token = jwt.encode(refresh_payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        refresh_token_id=refresh_token_id,
        refresh_token_expires_at=refresh_expires_at,
    )
