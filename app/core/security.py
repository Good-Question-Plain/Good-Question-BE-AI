import logging

import httpx
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from app.core.config import settings

logger = logging.getLogger(__name__)

_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    url = f"{settings.supabase_base_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    logger.info("JWKS 로드 완료: %d keys", len(_jwks_cache.get("keys", [])))
    return _jwks_cache


async def verify_supabase_token(token: str) -> dict:
    global _jwks_cache

    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    alg = header.get("alg", "ES256")

    jwks = await _get_jwks()
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)

    # 키를 찾지 못하면 캐시 갱신 후 재시도 (키 로테이션 대응)
    if key is None:
        _jwks_cache = None
        jwks = await _get_jwks()
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)

    if key is None:
        raise JWTError(f"No matching signing key for kid={kid!r}")

    try:
        return jwt.decode(token, key, algorithms=[alg], audience="authenticated")
    except ExpiredSignatureError as e:
        logger.warning("JWT 토큰 만료: %s", e)
        raise
    except JWTClaimsError as e:
        logger.warning("JWT claim 검증 실패: %s", e)
        raise
    except JWTError as e:
        logger.warning("JWT 검증 실패: %s", e)
        raise
