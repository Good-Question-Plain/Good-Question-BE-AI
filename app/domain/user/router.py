import uuid as _uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import (
    CurrentUser,
    CurrentUserWithEmail,
    DBSession,
    S3ClientDep,
)
from app.core.exceptions import BadRequestError
from app.core.s3 import generate_presigned_upload_url
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    MypageResponse,
    ParentResponse,
    ParentUpdateRequest,
    PresignedUrlRequest,
    PresignedUrlResponse,
)
from app.domain.user.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _get_service(db: DBSession, s3: S3ClientDep) -> UserService:
    return UserService(db, s3)


@router.get("/mypage", response_model=MypageResponse)
async def get_mypage(
    user_with_email: CurrentUserWithEmail,
    service: UserService = Depends(_get_service),
):
    parent, email = user_with_email
    return await service.get_mypage(parent, email)


@router.get("/me", response_model=ParentResponse)
async def get_me(
    user_with_email: CurrentUserWithEmail,
    service: UserService = Depends(_get_service),
):
    parent, email = user_with_email
    return service.get_me(parent, email)


@router.patch("/me", response_model=ParentResponse)
async def update_me(
    body: ParentUpdateRequest,
    user_with_email: CurrentUserWithEmail,
    service: UserService = Depends(_get_service),
):
    parent, email = user_with_email
    if body.name is None and body.profile_image_url is None:
        raise BadRequestError("수정할 항목을 하나 이상 입력해주세요.")
    if body.name is not None and not body.name.strip():
        raise BadRequestError("이름은 비워둘 수 없습니다.")
    return await service.update_me(parent, body, email)


@router.post("/profile-image/presigned-url", response_model=PresignedUrlResponse)
async def get_profile_image_presigned_url(
    body: PresignedUrlRequest,
    user: CurrentUser,
    s3: S3ClientDep,
):
    if not body.content_type.startswith("image/"):
        raise BadRequestError("이미지 파일만 업로드할 수 있습니다.")
    ext = body.content_type.split("/")[-1]
    if body.target == "parent":
        key = f"profiles/parents/{user.id}/{_uuid.uuid4()}.{ext}"
    else:
        key = f"profiles/children/{user.id}/{_uuid.uuid4()}.{ext}"
    upload_url = generate_presigned_upload_url(s3, key, body.content_type)
    return PresignedUrlResponse(upload_url=upload_url, object_key=key)


@router.get("/me/children", response_model=list[ChildResponse])
async def get_children(
    user: CurrentUser,
    service: UserService = Depends(_get_service),
):
    return await service.get_children(user)


@router.post("/me/children", response_model=ChildResponse, status_code=201)
async def create_child(
    body: ChildCreateRequest,
    user: CurrentUser,
    service: UserService = Depends(_get_service),
):
    return await service.create_child(user, body)


@router.patch("/me/children/{child_id}", response_model=ChildResponse)
async def update_child(
    child_id: _uuid.UUID,
    body: ChildUpdateRequest,
    user: CurrentUser,
    service: UserService = Depends(_get_service),
):
    if body.name is None and body.profile_image_url is None and body.birth_year is None:
        raise BadRequestError("수정할 항목을 하나 이상 입력해주세요.")
    if body.name is not None and not body.name.strip():
        raise BadRequestError("이름은 비워둘 수 없습니다.")
    return await service.update_child(user, child_id, body)
