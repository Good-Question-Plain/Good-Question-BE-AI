import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.story import Story
from app.models.story_session import StorySession

PUBLISHED = "published"


class StoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_published(
        self,
        category: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Story], int]:
        conditions = [Story.status == PUBLISHED]
        if category is not None:
            conditions.append(Story.topics.any(category))

        total = await self.db.scalar(
            select(func.count()).select_from(Story).where(*conditions)
        )
        result = await self.db.execute(
            select(Story)
            .where(*conditions)
            .order_by(Story.created_at.desc(), Story.id)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total or 0

    async def list_recommended(self, child_id: uuid.UUID, limit: int) -> list[Story]:
        already_started = (
            select(StorySession.id)
            .where(
                StorySession.child_id == child_id,
                StorySession.story_id == Story.id,
            )
            .exists()
        )
        result = await self.db.execute(
            select(Story)
            .where(Story.status == PUBLISHED)
            .order_by(already_started.asc(), Story.created_at.desc(), Story.id)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_published_with_scenes(self, story_id: uuid.UUID) -> Story | None:
        result = await self.db.execute(
            select(Story)
            .options(selectinload(Story.scenes))
            .where(Story.id == story_id, Story.status == PUBLISHED)
        )
        return result.scalar_one_or_none()
