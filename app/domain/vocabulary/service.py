import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.domain.vocabulary.repository import VocabularyRepository
from app.domain.vocabulary.schema import VocabularyDetail, VocabularyListItem
from app.models.child import Child
from app.models.parent import Parent


class VocabularyService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = VocabularyRepository(db)
        self.db = db

    async def _verify_child_ownership(self, parent: Parent, child_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(Child).where(Child.id == child_id, Child.parent_id == parent.id)
        )
        if result.scalar_one_or_none() is None:
            raise ForbiddenError("해당 자녀 프로필에 접근할 수 없습니다.")

    async def get_list(
        self,
        parent: Parent,
        child_id: uuid.UUID,
        story_id: uuid.UUID | None = None,
    ) -> list[VocabularyListItem]:
        await self._verify_child_ownership(parent, child_id)
        rows = await self.repo.get_list(child_id, story_id)
        return [
            VocabularyListItem(
                id=r.id,
                word=r.word,
                story_id=r.story_id,
                story_title=r.story_title,
                is_saved=r.is_saved,
            )
            for r in rows
        ]

    async def get_detail(
        self,
        parent: Parent,
        child_id: uuid.UUID,
        vocab_id: uuid.UUID,
    ) -> VocabularyDetail:
        await self._verify_child_ownership(parent, child_id)
        row = await self.repo.get_detail(vocab_id, child_id)
        if row is None:
            raise NotFoundError("단어를 찾을 수 없습니다.")
        return VocabularyDetail(
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

    async def save_word(
        self,
        parent: Parent,
        child_id: uuid.UUID,
        vocab_id: uuid.UUID,
    ) -> None:
        await self._verify_child_ownership(parent, child_id)
        existing = await self.repo.get_child_vocabulary(child_id, vocab_id)
        if existing is not None:
            raise ConflictError("이미 저장된 단어입니다.")
        await self.repo.save(child_id, vocab_id)

    async def unsave_word(
        self,
        parent: Parent,
        child_id: uuid.UUID,
        vocab_id: uuid.UUID,
    ) -> None:
        await self._verify_child_ownership(parent, child_id)
        deleted = await self.repo.unsave(child_id, vocab_id)
        if not deleted:
            raise NotFoundError("저장된 단어를 찾을 수 없습니다.")
