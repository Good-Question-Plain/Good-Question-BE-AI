from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user.repository import ChildRepository
from app.domain.user.schema import (
    ChildCreateRequest,
    ChildResponse,
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
        child = await self.repo.create(parent.id, data.name)
        return ChildResponse.model_validate(child)
