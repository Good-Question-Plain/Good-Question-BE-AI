import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.s3 import check_object_exists, resolve_image_url
from app.domain.user.repository import ChildRepository, ParentRepository
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    MypageResponse,
    ParentResponse,
    ParentUpdateRequest,
)
from app.models.child import Child
from app.models.parent import Parent


class UserService:
    def __init__(self, db: AsyncSession, s3: Any) -> None:
        self.repo = ChildRepository(db)
        self.parent_repo = ParentRepository(db)
        self.s3 = s3

    def _child_response(self, child: Child) -> ChildResponse:
        return ChildResponse(
            id=child.id,
            name=child.name,
            profile_image_url=resolve_image_url(self.s3, child.profile_image_url),
            birth_year=child.birth_year,
        )

    def _parent_response(self, parent: Parent, email: str) -> ParentResponse:
        return ParentResponse(
            id=parent.id,
            name=parent.name,
            email=email,
            profile_image_url=resolve_image_url(self.s3, parent.profile_image_url),
        )

    def get_me(self, parent: Parent, email: str) -> ParentResponse:
        return self._parent_response(parent, email)

    async def update_me(
        self, parent: Parent, data: ParentUpdateRequest, email: str
    ) -> ParentResponse:
        updated = await self.parent_repo.update(parent, data)
        return self._parent_response(updated, email)

    async def get_children(self, parent: Parent) -> list[ChildResponse]:
        children = await self.repo.get_all_by_parent(parent.id)
        return [self._child_response(c) for c in children]

    async def _validate_image_key(self, key: str) -> None:
        if not key.startswith("http") and not await check_object_exists(self.s3, key):
            raise BadRequestError("프로필 이미지가 S3에 업로드되지 않았습니다.")

    async def create_child(
        self, parent: Parent, data: ChildCreateRequest
    ) -> ChildResponse:
        await self._validate_image_key(data.profile_image_url)
        child = await self.repo.create(parent.id, data.name, data.profile_image_url)
        return self._child_response(child)

    async def update_child(
        self, parent: Parent, child_id: uuid.UUID, data: ChildUpdateRequest
    ) -> ChildResponse:
        child = await self.repo.get_by_id_and_parent(child_id, parent.id)
        if child is None:
            raise NotFoundError("자녀 프로필을 찾을 수 없습니다.")
        if data.profile_image_url is not None:
            await self._validate_image_key(data.profile_image_url)
        updated = await self.repo.update(child, data)
        return self._child_response(updated)

    async def get_mypage(self, parent: Parent, email: str) -> MypageResponse:
        children = await self.repo.get_all_by_parent(parent.id)
        return MypageResponse(
            parent=self._parent_response(parent, email),
            children=[self._child_response(c) for c in children],
        )
