import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.child import Child
from app.models.message import Message
from app.models.report import LearningReport, ReportVocabulary
from app.models.story import Story, StoryScene
from app.models.story_session import StorySession
from app.models.vocabulary import ChildVocabulary, SceneVocabulary

CHILD_SPEAKER = "child"
SESSION_COMPLETED = "completed"


class ReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_child(self, child_id: uuid.UUID) -> Child | None:
        result = await self.db.execute(select(Child).where(Child.id == child_id))
        return result.scalar_one_or_none()

    async def get_latest_completed_session(
        self, child_id: uuid.UUID, story_id: uuid.UUID
    ) -> StorySession | None:
        result = await self.db.execute(
            select(StorySession)
            .options(joinedload(StorySession.story), joinedload(StorySession.child))
            .where(
                StorySession.child_id == child_id,
                StorySession.story_id == story_id,
                StorySession.status == SESSION_COMPLETED,
            )
            .order_by(StorySession.completed_at.desc().nullslast(), StorySession.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_session(self, session_id: uuid.UUID) -> StorySession | None:
        result = await self.db.execute(
            select(StorySession)
            .options(joinedload(StorySession.story), joinedload(StorySession.child))
            .where(StorySession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_report_by_session(self, session_id: uuid.UUID) -> LearningReport | None:
        result = await self.db.execute(
            select(LearningReport).where(LearningReport.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_report_detail(self, session_id: uuid.UUID) -> LearningReport | None:
        result = await self.db.execute(
            select(LearningReport)
            .options(selectinload(LearningReport.vocabularies))
            .where(LearningReport.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_report(self, report_id: uuid.UUID) -> LearningReport | None:
        result = await self.db.execute(
            select(LearningReport).where(LearningReport.id == report_id)
        )
        return result.scalar_one_or_none()

    async def create_generating_report(
        self, session: StorySession
    ) -> LearningReport:
        report = LearningReport(
            session_id=session.id,
            child_id=session.child_id,
            story_id=session.story_id,
            status="generating",
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def reset_to_generating(self, report: LearningReport) -> LearningReport:
        await self.db.execute(
            delete(ReportVocabulary).where(ReportVocabulary.report_id == report.id)
        )
        report.status = "generating"
        report.failure_reason = None
        report.completed_at = None
        report.story_topic_questions = []
        report.daily_life_questions = []
        report.representative_message_id = None
        report.representative_quote = None
        report.representative_reason = None
        report.representative_elements = []
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def list_child_utterances(self, session_id: uuid.UUID) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .options(joinedload(Message.utterance_analysis), joinedload(Message.scene))
            .where(Message.session_id == session_id, Message.speaker_type == CHILD_SPEAKER)
            .order_by(Message.turn_order)
        )
        return list(result.scalars().unique())

    async def list_session_messages(self, session_id: uuid.UUID) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.turn_order, Message.created_at)
        )
        return list(result.scalars().all())

    async def save_result(
        self,
        report: LearningReport,
        *,
        speech_summary: str,
        vocabulary_feedback: str,
        expression_patterns: list[str],
        expression_items: list[dict],
        logic_items: list[dict],
        story_topic_questions: list[dict],
        daily_life_questions: list[dict],
        vocabularies: list[dict],
        representative: dict | None,
        analyzer_name: str,
        report_version: str,
    ) -> None:
        report.speech_summary = speech_summary
        report.vocabulary_feedback = vocabulary_feedback
        report.expression_patterns = expression_patterns
        report.expression_items = expression_items
        report.logic_items = logic_items
        report.story_topic_questions = story_topic_questions
        report.daily_life_questions = daily_life_questions
        report.representative_message_id = representative["message_id"] if representative else None
        report.representative_quote = representative["text"] if representative else None
        report.representative_reason = representative["reason"] if representative else None
        report.representative_elements = representative["elements"] if representative else []
        report.analyzer_name = analyzer_name
        report.report_version = report_version
        report.status = "completed"
        report.failure_reason = None
        report.completed_at = datetime.now(UTC)

        self.db.add_all(
            [
                ReportVocabulary(
                    report_id=report.id,
                    child_id=report.child_id,
                    word=item["word"],
                    kind=item["kind"],
                    definition=item.get("definition"),
                    example_sentence=item.get("example_sentence"),
                )
                for item in vocabularies
            ]
        )
        await self.db.commit()

    async def mark_failed(self, report: LearningReport, reason: str) -> None:
        await self.db.rollback()
        report.status = "failed"
        report.failure_reason = reason
        await self.db.commit()

    async def get_neighbor_story_ids(
        self, report: LearningReport
    ) -> tuple[uuid.UUID | None, uuid.UUID | None]:
        """리포트 화면의 이전/다음 리포트 버튼용. 같은 아이의 리포트를 생성 순으로 훑는다."""
        previous = await self.db.scalar(
            select(LearningReport.story_id)
            .where(
                LearningReport.child_id == report.child_id,
                LearningReport.created_at < report.created_at,
            )
            .order_by(LearningReport.created_at.desc())
            .limit(1)
        )
        following = await self.db.scalar(
            select(LearningReport.story_id)
            .where(
                LearningReport.child_id == report.child_id,
                LearningReport.created_at > report.created_at,
            )
            .order_by(LearningReport.created_at)
            .limit(1)
        )
        return previous, following

    async def list_vocabularies(
        self,
        child_id: uuid.UUID,
        kind: str | None,
        limit: int,
        offset: int,
    ) -> tuple[int, list[ReportVocabulary]]:
        conditions = [ReportVocabulary.child_id == child_id]
        if kind:
            conditions.append(ReportVocabulary.kind == kind)

        total = await self.db.scalar(
            select(func.count()).select_from(ReportVocabulary).where(*conditions)
        )
        result = await self.db.execute(
            select(ReportVocabulary)
            .where(*conditions)
            .order_by(ReportVocabulary.created_at.desc(), ReportVocabulary.word)
            .limit(limit)
            .offset(offset)
        )
        return total or 0, list(result.scalars())

    async def list_session_curious_words(self, session_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(SceneVocabulary)
            .join(ChildVocabulary)
            .where(
                ChildVocabulary.session_id == session_id,
                ChildVocabulary.kind == "curious",
            )
            .order_by(ChildVocabulary.saved_at, SceneVocabulary.word)
        )
        return [
            {
                "word": row.word,
                "kind": "curious",
                "definition": row.definition,
                "example_sentence": row.example_sentence,
            }
            for row in result.scalars()
        ]

    async def list_curious_vocabularies(
        self,
        child_id: uuid.UUID,
        limit: int,
        offset: int,
    ) -> tuple[int, list[ChildVocabulary]]:
        conditions = [
            ChildVocabulary.child_id == child_id,
            ChildVocabulary.kind == "curious",
        ]
        total = await self.db.scalar(
            select(func.count()).select_from(ChildVocabulary).where(*conditions)
        )
        result = await self.db.execute(
            select(ChildVocabulary)
            .options(joinedload(ChildVocabulary.scene_vocabulary))
            .where(*conditions)
            .order_by(ChildVocabulary.saved_at.desc(), ChildVocabulary.id)
            .limit(limit)
            .offset(offset)
        )
        return total or 0, list(result.scalars().unique())


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
            definition=row.definition or "",
            usage_context=row.usage_context or "",
            example_sentence=row.example_sentence or "",
            audio_url=row.audio_url,
            story_id=row.story_id,
            story_title=row.story_title,
            is_saved=row.is_saved,
        )

    async def get_child_vocabulary(
        self, child_id: uuid.UUID, vocab_id: uuid.UUID
    ) -> ChildVocabulary | None:
        result = await self.db.execute(
            select(ChildVocabulary)
            .where(
                ChildVocabulary.child_id == child_id,
                ChildVocabulary.scene_vocabulary_id == vocab_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save(self, child_id: uuid.UUID, vocab_id: uuid.UUID) -> None:
        entry = ChildVocabulary(
            child_id=child_id,
            scene_vocabulary_id=vocab_id,
            kind="saved",
        )
        self.db.add(entry)
        await self.db.commit()

    async def unsave(self, child_id: uuid.UUID, vocab_id: uuid.UUID) -> bool:
        entry = await self.get_child_vocabulary(child_id, vocab_id)
        if entry is None:
            return False
        await self.db.delete(entry)
        await self.db.commit()
        return True
