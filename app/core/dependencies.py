from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings as _settings
from app.core.exceptions import UnauthorizedError
from app.core.redis import get_redis
from app.core.security import decode_token
from app.db.session import get_db
from app.models.caregiver import Caregiver

_http_bearer = HTTPBearer()


@lru_cache
def get_settings() -> Settings:
    return _settings


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_http_bearer),
    db: AsyncSession = Depends(get_db),
) -> Caregiver:
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedError("유효하지 않은 토큰입니다.")

    if payload.get("type") != "access":
        raise UnauthorizedError("유효하지 않은 토큰 타입입니다.")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("유효하지 않은 토큰입니다.")

    from app.domain.auth.repository import CaregiverRepository
    caregiver = await CaregiverRepository(db).get_by_id(user_id)
    if not caregiver:
        raise UnauthorizedError("존재하지 않는 사용자입니다.")
    return caregiver


SettingsDep = Annotated[Settings, Depends(get_settings)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]
CurrentUser = Annotated[Caregiver, Depends(get_current_user)]
