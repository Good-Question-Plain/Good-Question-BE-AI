import random
import string

import httpx
from jose import JWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.smtp import send_otp_email, send_reset_password_email
from app.domain.auth.repository import CaregiverRepository
from app.domain.auth.schema import TokenResponse
from app.models.caregiver import SocialProvider

_PROVIDER_CONFIG: dict[str, dict] = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
    },
    "kakao": {
        "auth_url": "https://kauth.kakao.com/oauth/authorize",
        "token_url": "https://kauth.kakao.com/oauth/token",
        "userinfo_url": "https://kapi.kakao.com/v2/user/me",
        "scope": "profile_nickname account_email",
    },
    "naver": {
        "auth_url": "https://nid.naver.com/oauth2.0/authorize",
        "token_url": "https://nid.naver.com/oauth2.0/token",
        "userinfo_url": "https://openapi.naver.com/v1/nid/me",
        "scope": "name email",
    },
}

_CLIENT_ID: dict[str, str] = {
    "google": "GOOGLE_CLIENT_ID",
    "kakao": "KAKAO_CLIENT_ID",
    "naver": "NAVER_CLIENT_ID",
}

_CLIENT_SECRET: dict[str, str] = {
    "google": "GOOGLE_CLIENT_SECRET",
    "kakao": "KAKAO_CLIENT_SECRET",
    "naver": "NAVER_CLIENT_SECRET",
}


class AuthService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.repo = CaregiverRepository(db)
        self.redis = redis

    async def register(self, email: str, password: str) -> None:
        if await self.repo.get_by_email(email):
            raise ConflictError("이미 사용 중인 이메일입니다.")

        hashed = hash_password(password)
        await self.repo.create(email=email, hashed_password=hashed)

        otp = "".join(random.choices(string.digits, k=6))
        await self.redis.set(f"otp:{email}", otp, ex=settings.OTP_EXPIRE_MINUTES * 60)
        await send_otp_email(email, otp)

    async def verify_email(self, email: str, otp: str) -> None:
        stored = await self.redis.get(f"otp:{email}")
        if not stored or stored != otp:
            raise BadRequestError("유효하지 않거나 만료된 인증 코드입니다.")

        caregiver = await self.repo.get_by_email(email)
        if not caregiver:
            raise BadRequestError("존재하지 않는 계정입니다.")

        await self.repo.set_verified(caregiver)
        await self.redis.delete(f"otp:{email}")

    async def login(self, email: str, password: str) -> TokenResponse:
        caregiver = await self.repo.get_by_email(email)
        if not caregiver or not caregiver.hashed_password:
            raise UnauthorizedError("이메일 또는 비밀번호가 올바르지 않습니다.")
        if not verify_password(password, caregiver.hashed_password):
            raise UnauthorizedError("이메일 또는 비밀번호가 올바르지 않습니다.")
        if not caregiver.is_verified:
            raise ForbiddenError("이메일 인증이 필요합니다.")

        return await self._issue_tokens(str(caregiver.id))

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise UnauthorizedError("유효하지 않은 토큰입니다.")

        if payload.get("type") != "refresh":
            raise UnauthorizedError("유효하지 않은 토큰 타입입니다.")

        user_id: str = payload.get("sub", "")
        stored = await self.redis.get(f"refresh:{user_id}")
        if not stored or stored != refresh_token:
            raise UnauthorizedError("만료되었거나 유효하지 않은 리프레시 토큰입니다.")

        return TokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=refresh_token,
        )

    async def logout(self, user_id: str) -> None:
        await self.redis.delete(f"refresh:{user_id}")

    async def forgot_password(self, email: str) -> None:
        caregiver = await self.repo.get_by_email(email)
        if not caregiver or caregiver.hashed_password is None:
            return  # 이메일 존재 여부 노출 금지

        otp = "".join(random.choices(string.digits, k=6))
        await self.redis.set(f"reset:{email}", otp, ex=settings.OTP_EXPIRE_MINUTES * 60)
        await send_reset_password_email(email, otp)

    async def reset_password(self, email: str, otp: str, new_password: str) -> None:
        caregiver = await self.repo.get_by_email(email)
        if not caregiver or caregiver.hashed_password is None:
            raise BadRequestError("비밀번호 재설정이 불가능한 계정입니다.")

        stored = await self.redis.get(f"reset:{email}")
        if not stored or stored != otp:
            raise BadRequestError("유효하지 않거나 만료된 인증 코드입니다.")

        await self.repo.update_password(caregiver, hash_password(new_password))
        await self.redis.delete(f"reset:{email}")

    async def delete_account(self, user_id: str) -> None:
        caregiver = await self.repo.get_by_id(user_id)
        if not caregiver:
            raise BadRequestError("존재하지 않는 계정입니다.")

        await self.redis.delete(f"refresh:{user_id}")
        await self.repo.delete(caregiver)

    async def social_callback(self, provider: str, code: str, redirect_uri: str) -> TokenResponse:
        cfg = self._get_provider_config(provider)

        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                cfg["token_url"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": getattr(settings, _CLIENT_ID[provider]),
                    "client_secret": getattr(settings, _CLIENT_SECRET[provider]),
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            provider_token = token_resp.json()["access_token"]

            userinfo_resp = await client.get(
                cfg["userinfo_url"],
                headers={"Authorization": f"Bearer {provider_token}"},
            )
            userinfo_resp.raise_for_status()
            userinfo = userinfo_resp.json()

        email, social_id = self._extract_userinfo(provider, userinfo)
        provider_enum = SocialProvider(provider)

        caregiver = await self.repo.get_by_social(provider_enum, social_id)
        if not caregiver:
            caregiver = await self.repo.get_by_email(email)
            if caregiver:
                if not caregiver.is_verified:
                    await self.repo.set_verified(caregiver)
            else:
                caregiver = await self.repo.create(
                    email=email,
                    social_provider=provider_enum,
                    social_id=social_id,
                    is_verified=True,
                )

        return await self._issue_tokens(str(caregiver.id))

    async def _issue_tokens(self, user_id: str) -> TokenResponse:
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        await self.redis.set(
            f"refresh:{user_id}",
            refresh_token,
            ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    @staticmethod
    def _get_provider_config(provider: str) -> dict:
        if provider not in _PROVIDER_CONFIG:
            raise BadRequestError(f"지원하지 않는 소셜 로그인 제공자입니다: {provider}")
        return _PROVIDER_CONFIG[provider]

    @staticmethod
    def _extract_userinfo(provider: str, userinfo: dict) -> tuple[str, str]:
        if provider == "google":
            return userinfo["email"], str(userinfo["id"])
        if provider == "kakao":
            account = userinfo.get("kakao_account", {})
            return account["email"], str(userinfo["id"])
        if provider == "naver":
            response = userinfo.get("response", {})
            return response["email"], str(response["id"])
        raise BadRequestError(f"지원하지 않는 제공자: {provider}")
