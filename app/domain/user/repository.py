import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user.schema import ChildUpdateRequest, ParentUpdateRequest
from app.models.child import Child
from app.models.parent import Parent


class ParentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def update(self, parent: Parent, data: ParentUpdateRequest) -> Parent:
        if data.name is not None:
            parent.name = data.name
        if data.profile_image_url is not None:
            parent.profile_image_url = data.profile_image_url
        await self.db.commit()
        await self.db.refresh(parent)
        return parent


class ChildRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all_by_parent(self, parent_id: uuid.UUID) -> list[Child]:
        result = await self.db.execute(
            select(Child).where(Child.parent_id == parent_id)
        )
        return list(result.scalars().all())

    async def get_by_id_and_parent(
        self, child_id: uuid.UUID, parent_id: uuid.UUID
    ) -> Child | None:
        result = await self.db.execute(
            select(Child).where(Child.id == child_id, Child.parent_id == parent_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self, parent_id: uuid.UUID, name: str, profile_image_url: str
    ) -> Child:
        child = Child(
            parent_id=parent_id, name=name, profile_image_url=profile_image_url
        )
        self.db.add(child)
        await self.db.commit()
        await self.db.refresh(child)
        return child

    async def update(self, child: Child, data: ChildUpdateRequest) -> Child:
        if data.name is not None:
            child.name = data.name
        if data.profile_image_url is not None:
            child.profile_image_url = data.profile_image_url
        if data.birth_year is not None:
            child.birth_year = data.birth_year
        await self.db.commit()
        await self.db.refresh(child)
        return child
