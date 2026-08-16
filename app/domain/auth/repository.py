import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parent import Parent


class ParentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, parent_id: str) -> Parent | None:
        result = await self.db.execute(
            select(Parent).where(Parent.id == uuid.UUID(parent_id))
        )
        return result.scalar_one_or_none()

    async def create(self, parent_id: str, name: str) -> Parent:
        parent = Parent(id=uuid.UUID(parent_id), name=name)
        self.db.add(parent)
        await self.db.commit()
        await self.db.refresh(parent)
        return parent

    async def delete(self, parent: Parent) -> None:
        await self.db.delete(parent)
        await self.db.commit()
