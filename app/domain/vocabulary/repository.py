import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import Story, StoryScene
from app.models.story_session import StorySession
from app.models.vocabulary import ChildVocabulary, SceneVocabulary


@dataclass
class VocabularyRow:
    id: uuid.UUID
    word: str
    story_id: uuid.UUID
    story_title: str
    is_saved: bool


@dataclass
class VocabularyDetailRow:
    id: uuid.UUID
    word: str
    definition: str
    usage_context: str
    example_sentence: str
    audio_url: str | None
    story_id: uuid.UUID
    story_title: str
    is_saved: bool


class VocabularyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_list(
        self,
        child_id: uuid.UUID,
        story_id: uuid.UUID | None = None,
    ) -> list[VocabularyRow]:
        is_saved_col = (ChildVocabulary.id != None).label("is_saved")  # noqa: E711

        stmt = (
            select(
                SceneVocabulary.id,
                SceneVocabulary.word,
                Story.id.label("story_id"),
                Story.title.label("story_title"),
                is_saved_col,
            )
            .join(StoryScene, SceneVocabulary.scene_id == StoryScene.id)
            .join(Story, StoryScene.story_id == Story.id)
            .join(
                StorySession,
                (StorySession.story_id == Story.id) & (StorySession.child_id == child_id),
            )
            .outerjoin(
                ChildVocabulary,
                (ChildVocabulary.scene_vocabulary_id == SceneVocabulary.id)
                & (ChildVocabulary.child_id == child_id),
            )
            .distinct(SceneVocabulary.id)
            .order_by(SceneVocabulary.id)
        )

        if story_id is not None:
            stmt = stmt.where(Story.id == story_id)

        result = await self.db.execute(stmt)
        return [
            VocabularyRow(
                id=row.id,
                word=row.word,
                story_id=row.story_id,
                story_title=row.story_title,
                is_saved=row.is_saved,
            )
            for row in result.all()
        ]

    async def get_detail(
        self,
        vocab_id: uuid.UUID,
        child_id: uuid.UUID,
    ) -> VocabularyDetailRow | None:
        stmt = (
            select(
                SceneVocabulary.id,
                SceneVocabulary.word,
                SceneVocabulary.definition,
                SceneVocabulary.usage_context,
                SceneVocabulary.example_sentence,
                SceneVocabulary.audio_url,
                Story.id.label("story_id"),
                Story.title.label("story_title"),
                (ChildVocabulary.id != None).label("is_saved"),  # noqa: E711
            )
            .join(StoryScene, SceneVocabulary.scene_id == StoryScene.id)
            .join(Story, StoryScene.story_id == Story.id)
            .join(
                StorySession,
                (StorySession.story_id == Story.id) & (StorySession.child_id == child_id),
            )
            .outerjoin(
                ChildVocabulary,
                (ChildVocabulary.scene_vocabulary_id == SceneVocabulary.id)
                & (ChildVocabulary.child_id == child_id),
            )
            .where(SceneVocabulary.id == vocab_id)
            .limit(1)
        )

        result = await self.db.execute(stmt)
        row = result.first()
        if row is None:
            return None

        return VocabularyDetailRow(
            id=row.id,
            word=row.word,
            definition=row.definition,
            usage_context=row.usage_context,
            example_sentence=row.example_sentence,
            audio_url=row.audio_url,
            story_id=row.story_id,
            story_title=row.story_title,
            is_saved=row.is_saved,
        )

    async def get_child_vocabulary(
        self, child_id: uuid.UUID, vocab_id: uuid.UUID
    ) -> ChildVocabulary | None:
        result = await self.db.execute(
            select(ChildVocabulary).where(
                ChildVocabulary.child_id == child_id,
                ChildVocabulary.scene_vocabulary_id == vocab_id,
            )
        )
        return result.scalar_one_or_none()

    async def save(self, child_id: uuid.UUID, vocab_id: uuid.UUID) -> None:
        entry = ChildVocabulary(child_id=child_id, scene_vocabulary_id=vocab_id)
        self.db.add(entry)
        await self.db.commit()

    async def unsave(self, child_id: uuid.UUID, vocab_id: uuid.UUID) -> bool:
        entry = await self.get_child_vocabulary(child_id, vocab_id)
        if entry is None:
            return False
        await self.db.delete(entry)
        await self.db.commit()
        return True
