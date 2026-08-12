import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.child import Child


class ChildRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all_by_parent(self, parent_id: uuid.UUID) -> list[Child]:
        result = await self.db.execute(
            select(Child).where(Child.parent_id == parent_id)
        )
        return list(result.scalars().all())

    async def create(self, parent_id: uuid.UUID, name: str) -> Child:
        child = Child(parent_id=parent_id, name=name)
        self.db.add(child)
        await self.db.commit()
        await self.db.refresh(child)
        return child
