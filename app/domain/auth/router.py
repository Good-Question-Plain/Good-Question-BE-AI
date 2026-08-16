from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, CurrentUserWithEmail, DBSession, SupabaseUserID
from app.domain.auth.schema import MessageResponse, SyncProfileRequest, VerifyPasswordRequest
from app.domain.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_service(db: DBSession) -> AuthService:
    return AuthService(db)


@router.post("/sync-profile", response_model=MessageResponse, status_code=201)
async def sync_profile(
    body: SyncProfileRequest,
    user_id: SupabaseUserID,
    service: AuthService = Depends(_get_service),
):
    await service.sync_profile(user_id, body.name)
    return MessageResponse(message="프로필이 등록되었습니다.")


@router.post("/verify-password", response_model=MessageResponse)
async def verify_password(
    body: VerifyPasswordRequest,
    user_with_email: CurrentUserWithEmail,
    service: AuthService = Depends(_get_service),
):
    _, email = user_with_email
    await service.verify_password(email, body.password)
    return MessageResponse(message="인증되었습니다.")


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    user: CurrentUser,
    service: AuthService = Depends(_get_service),
):
    await service.delete_account(user)
    return MessageResponse(message="회원탈퇴가 완료되었습니다.")
