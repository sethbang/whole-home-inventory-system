import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import database, models
from .settings import settings

logger = logging.getLogger(__name__)

# Fixed UUID v4 for the development-only bypass user.
DEV_USER_ID = uuid.UUID("a7a41c99-5555-4191-9b62-5e39b347b515")

DEV_USER = models.User(
    id=DEV_USER_ID,
    email="admin@example.com",
    username="admin",
    hashed_password="",
    is_active=True,
    created_at=datetime.utcnow(),
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
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
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: Optional[str] = payload.get("sub")
    except jwt.InvalidTokenError:
        raise _credentials_error()

    if username is None:
        raise _credentials_error()

    user = db.query(models.User).filter(models.User.username == username).first()
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


async def get_current_active_user_or_none(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(database.get_db),
) -> Optional[models.User]:
    if settings.BYPASS_AUTH:
        return DEV_USER

    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: Optional[str] = payload.get("sub")
    except jwt.InvalidTokenError:
        return None

    if not username:
        return None

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not user.is_active:
        return None
    return user
