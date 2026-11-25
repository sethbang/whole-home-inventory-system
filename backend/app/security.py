import logging
import uuid
from datetime import timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import database, models
from .settings import settings
from .utctime import utcnow

logger = logging.getLogger(__name__)

# Fixed UUID v4 for the development-only bypass user.
DEV_USER_ID = uuid.UUID("a7a41c99-5555-4191-9b62-5e39b347b515")

DEV_USER = models.User(
    id=DEV_USER_ID,
    email="admin@example.com",
    username="admin",
    hashed_password="",
    is_active=True,
    is_admin=True,
    created_at=utcnow(),
)

# bcrypt only reads the first 72 bytes of a password. passlib 1.7.4 (used
# until v3.3.x) silently truncated longer input on both hash and verify, so
# existing hashes for long passwords are hashes of the truncated bytes.
# bcrypt>=5 raises instead of truncating, so we truncate explicitly to keep
# those users able to log in. New passwords over the limit are rejected at
# the schema layer (see schemas.UserCreate).
BCRYPT_MAX_PASSWORD_BYTES = 72


class OptionalOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request = None) -> Optional[str]:
        if settings.BYPASS_AUTH:
            return "dev_token"
        try:
            return await super().__call__(request)
        except HTTPException:
            return None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
oauth2_scheme_optional = OptionalOAuth2PasswordBearer(tokenUrl="token")


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_BYTES]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            _password_bytes(plain_password), hashed_password.encode("utf-8")
        )
    except ValueError:
        # Empty or malformed stored hash: treat as a failed login, not a 500.
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("ascii")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _credentials_error(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
) -> models.User:
    if settings.BYPASS_AUTH:
        return DEV_USER

    if not token:
        raise _credentials_error("Not authenticated")

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: Optional[str] = payload.get("sub")
    except jwt.InvalidTokenError:
        raise _credentials_error()

    if username is None:
        raise _credentials_error()

    user = db.execute(
        select(models.User).where(models.User.username == username)
    ).scalar_one_or_none()
    if user is None:
        raise _credentials_error("User not found")
    return user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if settings.BYPASS_AUTH:
        return DEV_USER
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def require_admin(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """Reject non-admin users with 403.

    Used by the /api/llm-config router (and any future operator-only
    surface). The bypass user is treated as admin so the dev experience
    matches production. ``is_admin`` is a v3.2-introduced column —
    older user rows that haven't been migrated default to False.
    """
    if settings.BYPASS_AUTH:
        return DEV_USER
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


async def get_current_active_user_or_none(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(database.get_db),
) -> Optional[models.User]:
    if settings.BYPASS_AUTH:
        return DEV_USER

    if not token:
        return None

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: Optional[str] = payload.get("sub")
    except jwt.InvalidTokenError:
        return None

    if not username:
        return None

    user = db.execute(
        select(models.User).where(models.User.username == username)
    ).scalar_one_or_none()
    if not user or not user.is_active:
        return None
    return user
