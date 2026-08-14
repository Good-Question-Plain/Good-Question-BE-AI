import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.child import Child
from app.models.message import Message, UtteranceAnalysis
from app.models.story import Story, StoryScene
from app.models.story_session import StorySession

PUBLISHED = "published"
IN_PROGRESS = "in_progress"
COMPLETED = "completed"


class ProgressRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_child(self, child_id: uuid.UUID, parent_id: uuid.UUID) -> Child | None:
        result = await self.db.execute(
            select(Child).where(Child.id == child_id, Child.parent_id == parent_id)
        )
        return result.scalar_one_or_none()

    async def get_published_story(self, story_id: uuid.UUID) -> Story | None:
        result = await self.db.execute(
            select(Story)
            .options(selectinload(Story.scenes))
            .where(Story.id == story_id, Story.status == PUBLISHED)
        )
        return result.scalar_one_or_none()

    async def count_scenes(self, story_id: uuid.UUID) -> int:
        total = await self.db.scalar(
            select(func.count())
            .select_from(StoryScene)
            .where(StoryScene.story_id == story_id)
        )
        return total or 0

    async def get_scene(
        self, story_id: uuid.UUID, scene_order: int
    ) -> StoryScene | None:
        result = await self.db.execute(
            select(StoryScene).where(
                StoryScene.story_id == story_id,
                StoryScene.scene_order == scene_order,
            )
        )
        return result.scalar_one_or_none()

    async def get_in_progress(self, child_id: uuid.UUID) -> StorySession | None:
        result = await self.db.execute(
            select(StorySession)
            .options(
                selectinload(StorySession.story),
                selectinload(StorySession.current_scene),
            )
            .where(
                StorySession.child_id == child_id,
                StorySession.status == IN_PROGRESS,
            )
            .order_by(StorySession.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_latest_for_story(
        self, child_id: uuid.UUID, story_id: uuid.UUID
    ) -> StorySession | None:
        result = await self.db.execute(
            select(StorySession)
            .options(
                selectinload(StorySession.story),
                selectinload(StorySession.current_scene),
            )
            .where(
                StorySession.child_id == child_id,
                StorySession.story_id == story_id,
            )
            .order_by(StorySession.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_session(
        self, child_id: uuid.UUID, story_id: uuid.UUID, scene_id: uuid.UUID
    ) -> StorySession:
        session = StorySession(
            child_id=child_id,
            story_id=story_id,
            current_scene_id=scene_id,
            status=IN_PROGRESS,
        )
        self.db.add(session)
        await self.db.commit()
        return await self.get_latest_for_story(child_id, story_id)  # type: ignore[return-value]

    async def save(self, session: StorySession) -> StorySession:
        session.last_activity_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def scene_has_messages(
        self, session_id: uuid.UUID, scene_id: uuid.UUID
    ) -> bool:
        total = await self.db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.session_id == session_id, Message.scene_id == scene_id)
        )
        return bool(total)

    async def flush_turns(
        self,
        session_id: uuid.UUID,
        scene_id: uuid.UUID,
        turns: list[dict],
    ) -> None:
        for order, turn in enumerate(turns):
            message = Message(
                session_id=session_id,
                scene_id=scene_id,
                speaker_type=turn["speaker"],
                turn_order=order,
                text=turn["text"],
                stt_raw_text=turn.get("stt_raw_text"),
            )
            self.db.add(message)
            await self.db.flush()
            if turn["speaker"] == "child":
                self.db.add(
                    UtteranceAnalysis(
                        message_id=message.id,
                        utterance_validity=turn.get("validity", "valid"),
                    )
                )
        await self.db.commit()
