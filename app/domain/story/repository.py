import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.story import Story, StoryScene
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

    async def get_popular_stories(self, limit: int) -> list[Story]:
        session_count = func.count(StorySession.id).label("session_count")
        result = await self.db.execute(
            select(Story)
            .outerjoin(StorySession, StorySession.story_id == Story.id)
            .where(Story.status == PUBLISHED)
            .group_by(Story.id)
            .order_by(session_count.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_scenes(self, story_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(StoryScene.id)).where(StoryScene.story_id == story_id)
        )
        return result.scalar_one()

