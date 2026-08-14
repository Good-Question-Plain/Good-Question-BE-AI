import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.message import Message
from app.models.post_activity import PostActivityResult
from app.models.story import StoryScene
from app.models.story_session import StorySession
from app.models.vocabulary import SceneVocabulary


class PostActivityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_session(
        self, session_id: uuid.UUID, parent_id: uuid.UUID
    ) -> StorySession:
        result = await self.db.execute(
            select(StorySession)
            .options(selectinload(StorySession.child), selectinload(StorySession.story))
            .where(StorySession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise NotFoundError("세션을 찾을 수 없습니다.")
        if session.child.parent_id != parent_id:
            raise ForbiddenError("접근 권한이 없습니다.")
        return session

    async def get_or_create_result(
        self, session_id: uuid.UUID
    ) -> PostActivityResult:
        result = await self.db.execute(
            select(PostActivityResult).where(
                PostActivityResult.session_id == session_id
            )
        )
        activity = result.scalar_one_or_none()
        if activity is None:
            activity = PostActivityResult(session_id=session_id)
            self.db.add(activity)
            await self.db.commit()
            await self.db.refresh(activity)
        return activity

    async def get_scenes(self, story_id: uuid.UUID) -> list[StoryScene]:
        result = await self.db.execute(
            select(StoryScene)
            .where(StoryScene.story_id == story_id)
            .order_by(StoryScene.scene_order)
        )
        return list(result.scalars().all())

    async def get_vocabulary(self, story_id: uuid.UUID) -> list[SceneVocabulary]:
        result = await self.db.execute(
            select(SceneVocabulary)
            .join(StoryScene)
            .where(StoryScene.story_id == story_id)
        )
        return list(result.scalars().all())

    async def save_submit(
        self,
        activity: PostActivityResult,
        submitted_order: list[str],
        is_correct: bool,
        attempt_count: int,
    ) -> PostActivityResult:
        activity.submitted_order = submitted_order
        activity.is_order_correct = is_correct
        activity.attempt_count = attempt_count
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    async def save_retell(
        self,
        activity: PostActivityResult,
        retelling_text: str,
    ) -> PostActivityResult:
        activity.retelling_text = retelling_text
        activity.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    async def count_child_utterances(self, session_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Message.id)).where(
                Message.session_id == session_id,
                Message.speaker_type == "child",
            )
        )
        return result.scalar_one()

    async def count_story_vocabulary(self, story_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(SceneVocabulary.id))
            .join(StoryScene)
            .where(StoryScene.story_id == story_id)
        )
        return result.scalar_one()
