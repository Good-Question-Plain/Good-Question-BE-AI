import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import Story, StoryScene
from app.models.story_session import StorySession


class StoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_stories(self, topic: str | None = None) -> list[Story]:
        stmt = select(Story).where(Story.status == "published")

        if topic and topic != "전체":
            stmt = stmt.where(Story.topics.any(topic))
        stmt = stmt.order_by(Story.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_popular_stories(self, limit: int) -> list[Story]:
        session_count = func.count(StorySession.id).label("session_count")
        stmt = (
            select(Story)
            .outerjoin(StorySession, StorySession.story_id == Story.id)
            .where(Story.status == "published")
            .group_by(Story.id)
            .order_by(session_count.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_scenes(self, story_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(StoryScene.id)).where(StoryScene.story_id == story_id)
        )

        return result.scalar_one()
