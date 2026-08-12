import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.user.repository import ChildRepository
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    ParentResponse,
)
from app.models.parent import Parent


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ChildRepository(db)

    def get_me(self, parent: Parent, email: str) -> ParentResponse:
        return ParentResponse(id=parent.id, name=parent.name, email=email)

    async def get_children(self, parent: Parent) -> list[ChildResponse]:
        children = await self.repo.get_all_by_parent(parent.id)
        return [ChildResponse.model_validate(c) for c in children]

    async def create_child(
        self, parent: Parent, data: ChildCreateRequest
    ) -> ChildResponse:
        child = await self.repo.create(parent.id, data.name, data.birth_year)
        return ChildResponse.model_validate(child)

    async def update_child(
        self, parent: Parent, child_id: uuid.UUID, data: ChildUpdateRequest
    ) -> ChildResponse:
        child = await self.repo.get_by_id_and_parent(child_id, parent.id)
        if child is None:
            raise NotFoundError("자녀 프로필을 찾을 수 없습니다.")
        child = await self.repo.update(child, data.name, data.birth_year)
        return ChildResponse.model_validate(child)

    async def delete_child(self, parent: Parent, child_id: uuid.UUID) -> None:
        child = await self.repo.get_by_id_and_parent(child_id, parent.id)
        if child is None:
            raise NotFoundError("자녀 프로필을 찾을 수 없습니다.")
        await self.repo.delete(child)
