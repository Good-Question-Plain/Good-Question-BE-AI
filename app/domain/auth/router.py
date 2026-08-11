from typing import Literal

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession, RedisDep
from app.domain.auth.schema import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SocialCallbackRequest,
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


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    service: AuthService = Depends(_get_service),
):
    await service.forgot_password(body.email)
    return MessageResponse(message="비밀번호 재설정 메일이 발송되었습니다.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    service: AuthService = Depends(_get_service),
):
    await service.reset_password(body.email, body.otp, body.new_password)
    return MessageResponse(message="비밀번호가 변경되었습니다.")


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    user: CurrentUser,
    service: AuthService = Depends(_get_service),
):
    await service.delete_account(str(user.id))
    return MessageResponse(message="회원탈퇴가 완료되었습니다.")


@router.post("/{provider}/callback", response_model=TokenResponse)
async def social_callback(
    provider: Literal["google", "kakao", "naver"],
    body: SocialCallbackRequest,
    service: AuthService = Depends(_get_service),
):
    return await service.social_callback(provider, body.code, body.redirect_uri)
