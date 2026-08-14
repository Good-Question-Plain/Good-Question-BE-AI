import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.domain.post_activity.repository import PostActivityRepository
from app.domain.post_activity.schema import (
    ActivityResponse,
    RetellResponse,
    SceneCard,
    SubmitResponse,
    VocabularyItem,
)


class PostActivityService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = PostActivityRepository(db)

    async def get_activity(
        self, session_id: uuid.UUID, parent_id: uuid.UUID
    ) -> ActivityResponse:
        session = await self.repo.get_session(session_id, parent_id)
        if session.status != "completed":
            raise BadRequestError("세션이 아직 완료되지 않았습니다.")

        activity = await self.repo.get_or_create_result(session_id)
        scenes = await self.repo.get_scenes(session.story_id)

        cards = [
            SceneCard(scene_id=s.id, title=s.scene_title, image_url=s.image_url)
            for s in scenes
        ]
        random.shuffle(cards)

        is_completed = (
            activity.is_order_correct is True and activity.completed_at is not None
        )

        return ActivityResponse(
            attempt_count=activity.attempt_count,
            is_completed=is_completed,
            cards=cards,
        )

    async def submit_order(
        self,
        session_id: uuid.UUID,
        parent_id: uuid.UUID,
        submitted_order: list[uuid.UUID],
    ) -> SubmitResponse:
        session = await self.repo.get_session(session_id, parent_id)
        if session.status != "completed":
            raise BadRequestError("세션이 아직 완료되지 않았습니다.")
        activity = await self.repo.get_or_create_result(session_id)

        if activity.is_order_correct is True:
            raise BadRequestError("이미 정답 처리된 활동입니다.")

        scenes = await self.repo.get_scenes(session.story_id)

        if len(submitted_order) != len(scenes):
            raise BadRequestError("제출한 씬 수가 올바르지 않습니다.")

        correct_order = [s.id for s in scenes]
        is_correct = submitted_order == correct_order
        new_count = activity.attempt_count + 1

        updated = await self.repo.save_submit(
            activity,
            [str(sid) for sid in submitted_order],
            is_correct,
            new_count,
        )

        if not is_correct:
            return SubmitResponse(is_correct=False, attempt_count=updated.attempt_count)

        vocab_rows = await self.repo.get_vocabulary(session.story_id)
        vocabulary = [
            VocabularyItem(word=v.word, definition=v.definition) for v in vocab_rows
        ]
        return SubmitResponse(
            is_correct=True,
            attempt_count=updated.attempt_count,
            vocabulary=vocabulary,
        )

    async def save_retell(
        self,
        session_id: uuid.UUID,
        parent_id: uuid.UUID,
        retelling_text: str,
    ) -> RetellResponse:
        session = await self.repo.get_session(session_id, parent_id)
        activity = await self.repo.get_or_create_result(session_id)

        if not activity.is_order_correct:
            raise BadRequestError("순서 맞추기를 먼저 완료해야 합니다.")

        await self.repo.save_retell(activity, retelling_text)

        utterance_count = await self.repo.count_child_utterances(session_id)
        new_vocabulary_count = await self.repo.count_story_vocabulary(session.story_id)

        return RetellResponse(
            story_title=session.story.title,
            utterance_count=utterance_count,
            new_vocabulary_count=new_vocabulary_count,
        )
