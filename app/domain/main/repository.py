import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.models.story_session import StorySession

class MainRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active_session(self, child_id: uuid.UUID) -> StorySession | None:
        stmt = (
            select(StorySession)
            .options(
                joinedload(StorySession.story),
                joinedload(StorySession.current_scene),
            )
            .where(
                StorySession.child_id == child_id,
                StorySession.status.in_(["in_progress", "post_activity"]),
            )
            .order_by(StorySession.last_activity_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)

        return result.unique().scalar_one_or_none()
