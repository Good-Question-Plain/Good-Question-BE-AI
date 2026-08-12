import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, CurrentUserWithEmail, DBSession
from app.domain.auth.schema import MessageResponse
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    ParentResponse,
)
from app.domain.user.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _get_service(db: DBSession) -> UserService:
    return UserService(db)


@router.get("/me", response_model=ParentResponse)
async def get_me(
    user_with_email: CurrentUserWithEmail,
    service: UserService = Depends(_get_service),
):
    parent, email = user_with_email
    return service.get_me(parent, email)


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
    child_id: uuid.UUID,
    body: ChildUpdateRequest,
    user: CurrentUser,
    service: UserService = Depends(_get_service),
):
    return await service.update_child(user, child_id, body)


@router.delete("/me/children/{child_id}", response_model=MessageResponse)
async def delete_child(
    child_id: uuid.UUID,
    user: CurrentUser,
    service: UserService = Depends(_get_service),
):
    await service.delete_child(user, child_id)
    return MessageResponse(message="자녀 프로필이 삭제되었습니다.")
