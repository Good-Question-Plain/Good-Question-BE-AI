from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from app.core.dependencies import CurrentUser, DBSession, RedisDep
from app.domain.auth.schema import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.domain.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_service(db: DBSession, redis: RedisDep) -> AuthService:
    return AuthService(db, redis)


@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(_get_service),
):
    await service.register(body.email, body.password)
    return MessageResponse(message="인증 메일이 발송되었습니다. 이메일을 확인해주세요.")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    body: VerifyEmailRequest,
    service: AuthService = Depends(_get_service),
):
    await service.verify_email(body.email, body.otp)
    return MessageResponse(message="이메일 인증이 완료되었습니다.")


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    service: AuthService = Depends(_get_service),
):
    return await service.login(body.email, body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    service: AuthService = Depends(_get_service),
):
    return await service.refresh(body.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    user: CurrentUser,
    service: AuthService = Depends(_get_service),
):
    await service.logout(str(user.id))
    return MessageResponse(message="로그아웃 되었습니다.")


@router.get("/{provider}/login", response_class=RedirectResponse)
async def social_login(
    provider: Literal["google", "kakao", "naver"],
    service: AuthService = Depends(_get_service),
):
    url = await service.get_social_login_url(provider)
    return RedirectResponse(url=url)


@router.get("/{provider}/callback", response_model=TokenResponse)
async def social_callback(
    provider: Literal["google", "kakao", "naver"],
    code: str,
    state: str,
    service: AuthService = Depends(_get_service),
):
    return await service.social_callback(provider, code, state)
