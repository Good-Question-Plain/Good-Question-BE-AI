import uuid
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings as _settings
from app.core.exceptions import UnauthorizedError
from app.core.redis import get_redis
from app.core.security import verify_supabase_token
from app.db.session import get_db
from app.models.parent import Parent

_http_bearer = HTTPBearer()


@lru_cache
def get_settings() -> Settings:
    return _settings


def _extract_user_id(token: str) -> str:
    try:
        payload = verify_supabase_token(token)
    except JWTError:
        raise UnauthorizedError("유효하지 않은 토큰입니다.")
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("유효하지 않은 토큰입니다.")
    return user_id


async def get_supabase_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_http_bearer),
) -> str:
    return _extract_user_id(credentials.credentials)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_http_bearer),
    db: AsyncSession = Depends(get_db),
) -> Parent:
    user_id = _extract_user_id(credentials.credentials)
    result = await db.execute(select(Parent).where(Parent.id == uuid.UUID(user_id)))
    parent = result.scalar_one_or_none()
    if not parent:
        raise UnauthorizedError("프로필이 등록되지 않은 사용자입니다.")
    return parent


SettingsDep = Annotated[Settings, Depends(get_settings)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]
CurrentUser = Annotated[Parent, Depends(get_current_user)]
SupabaseUserID = Annotated[str, Depends(get_supabase_user_id)]
