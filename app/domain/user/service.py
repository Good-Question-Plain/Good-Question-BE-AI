import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.user.repository import ChildRepository, ParentRepository
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    MypageResponse,
    ParentResponse,
    ParentUpdateRequest,
)
from app.models.parent import Parent


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ChildRepository(db)
        self.parent_repo = ParentRepository(db)

    def get_me(self, parent: Parent, email: str) -> ParentResponse:
        return ParentResponse(
            id=parent.id,
            name=parent.name,
            email=email,
            profile_image_url=parent.profile_image_url,
        )

    async def update_me(
        self, parent: Parent, data: ParentUpdateRequest, email: str
    ) -> ParentResponse:
        updated = await self.parent_repo.update(parent, data)
        return ParentResponse(
            id=updated.id,
            name=updated.name,
            email=email,
            profile_image_url=updated.profile_image_url,
        )

    async def get_children(self, parent: Parent) -> list[ChildResponse]:
        children = await self.repo.get_all_by_parent(parent.id)
        return [ChildResponse.model_validate(c) for c in children]

    async def create_child(
        self, parent: Parent, data: ChildCreateRequest
    ) -> ChildResponse:
        child = await self.repo.create(parent.id, data.name, data.profile_image_url)
        return ChildResponse.model_validate(child)

    async def update_child(
        self, parent: Parent, child_id: uuid.UUID, data: ChildUpdateRequest
    ) -> ChildResponse:
        child = await self.repo.get_by_id_and_parent(child_id, parent.id)
        if child is None:
            raise NotFoundError("자녀 프로필을 찾을 수 없습니다.")
        updated = await self.repo.update(child, data)
        return ChildResponse.model_validate(updated)

    async def get_mypage(self, parent: Parent, email: str) -> MypageResponse:
        children = await self.repo.get_all_by_parent(parent.id)
        return MypageResponse(
            parent=ParentResponse(
                id=parent.id,
                name=parent.name,
                email=email,
                profile_image_url=parent.profile_image_url,
            ),
            children=[ChildResponse.model_validate(c) for c in children],
        )
