from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user.repository import ChildRepository, ParentRepository
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
    ParentResponse,
    ParentUpdateRequest,
)
from app.models.parent import Parent


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ChildRepository(db)
        self.parent_repo = ParentRepository(db)

    def get_me(self, parent: Parent, email: str) -> ParentResponse:
        return ParentResponse(id=parent.id, name=parent.name, email=email)

    async def update_me(
        self, parent: Parent, data: ParentUpdateRequest, email: str
    ) -> ParentResponse:
        updated = await self.parent_repo.update_parent(parent, data.name)
        return ParentResponse(id=updated.id, name=updated.name, email=email)

    async def get_children(self, parent: Parent) -> list[ChildResponse]:
        children = await self.repo.get_all_by_parent(parent.id)
        return [ChildResponse.model_validate(c) for c in children]

    async def create_child(
        self, parent: Parent, data: ChildCreateRequest
    ) -> ChildResponse:
        child = await self.repo.create(parent.id, data.name, data.profile_image_url)
        return ChildResponse.model_validate(child)
