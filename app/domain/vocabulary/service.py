import uuid
from dataclasses import asdict

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.db.session import AsyncSessionMaker
from app.domain.vocabulary.analyzer import (
    ReportContext,
    UtteranceInput,
    get_report_analyzer,
)
from app.domain.vocabulary.repository import ReportRepository, VocabularyRepository
from app.domain.vocabulary.schema import (
    ConversationPrompt,
    GenerateReportResponse,
    HomeConversationSection,
    ReportFeedbackItem,
    ReportResponse,
    RepresentativeUtterance,
    VocabularyDetail,
    VocabularyItem,
    VocabularyListItem,
    VocabularyListResponse,
    VocabularySection,
)
from app.models.child import Child
from app.models.parent import Parent
from app.models.message import Message
from app.models.report import LearningReport
from app.models.story_session import StorySession
from app.models.vocabulary import ChildVocabulary

_MAX_FAILURE_REASON_LENGTH = 500


def _element_tags(detected_elements: list | None) -> list[str]:
    """detected_elements JSONB — [{"element": "EMOTION", "evidence": "..."}] 에서 태그만 뽑는다."""
    return [
        item["element"]
        for item in detected_elements or []
        if isinstance(item, dict) and item.get("element")
    ]


class ReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ReportRepository(db)

    async def request_generation(
        self,
        parent_id: uuid.UUID,
        child_id: uuid.UUID,
        story_id: uuid.UUID,
        background_tasks: BackgroundTasks,
    ) -> GenerateReportResponse:
        session = await self._resolve_session(parent_id, child_id, story_id)
        report = await self.repo.get_report_by_session(session.id)

        if report is not None and report.status == "generating":
            raise ConflictError("리포트를 생성하는 중입니다. 잠시 후 다시 확인해주세요.")
        report = await self.enqueue_for_completed_session(session, background_tasks)
        if report is None:
            raise ConflictError("리포트를 생성하는 중입니다. 잠시 후 다시 확인해주세요.")
        return GenerateReportResponse(
            report_id=report.id, session_id=session.id, status=report.status  # type: ignore[arg-type]
        )

    async def enqueue_for_completed_session(
        self,
        session: StorySession,
        background_tasks: BackgroundTasks,
    ) -> LearningReport | None:
        """이야기 완료 시 호출. 기존 리포트가 있으면 이번 회차 내용으로 다시 생성한다."""
        report = await self.repo.get_report_by_session(session.id)
        if report is None:
            try:
                report = await self.repo.create_generating_report(session)
            except IntegrityError:
                return None
        elif report.status == "generating":
            return report
        else:
            report = await self.repo.reset_to_generating(report)

        background_tasks.add_task(generate_report_task, report.id)
        return report

    async def get_report(
        self, parent_id: uuid.UUID, child_id: uuid.UUID, story_id: uuid.UUID
    ) -> ReportResponse:
        session = await self._resolve_session(parent_id, child_id, story_id)
        report = await self.repo.get_report_detail(session.id)
        if report is None:
            raise NotFoundError("아직 생성된 리포트가 없습니다.")
        previous_story_id, next_story_id = await self.repo.get_neighbor_story_ids(report)
        return self._to_response(report, session, previous_story_id, next_story_id)

    async def list_vocabulary(
        self,
        parent_id: uuid.UUID,
        child_id: uuid.UUID,
        kind: str | None,
        limit: int,
        offset: int,
    ) -> VocabularyListResponse:
        await self._verify_child(parent_id, child_id)
        if kind == "curious":
            total, rows = await self.repo.list_curious_vocabularies(child_id, limit, offset)
            return VocabularyListResponse(
                total=total,
                items=[self._curious_item(row) for row in rows],
            )
        if kind == "used":
            total, rows = await self.repo.list_vocabularies(child_id, "used", limit, offset)
            return VocabularyListResponse(
                total=total,
                items=[VocabularyItem.model_validate(row) for row in rows],
            )

        curious_total, _ = await self.repo.list_curious_vocabularies(child_id, 1, 0)
        used_total, _ = await self.repo.list_vocabularies(child_id, "used", 1, 0)
        total = curious_total + used_total
        items: list[VocabularyItem] = []
        if offset < curious_total:
            take = min(limit, curious_total - offset)
            _, curious_rows = await self.repo.list_curious_vocabularies(
                child_id, take, offset
            )
            items.extend(self._curious_item(row) for row in curious_rows)
            remain = limit - len(items)
            if remain > 0:
                _, used_rows = await self.repo.list_vocabularies(
                    child_id, "used", remain, 0
                )
                items.extend(VocabularyItem.model_validate(row) for row in used_rows)
        else:
            _, used_rows = await self.repo.list_vocabularies(
                child_id, "used", limit, offset - curious_total
            )
            items.extend(VocabularyItem.model_validate(row) for row in used_rows)
        return VocabularyListResponse(total=total, items=items)

    async def run_generation(self, report_id: uuid.UUID) -> None:
        """백그라운드 실행 진입점. 예외를 밖으로 던지지 않고 리포트 상태에 기록한다."""
        report = await self.repo.get_report(report_id)
        if report is None or report.status != "generating":
            return

        try:
            draft = await self._build_draft(report)
        except Exception as exc:
            await self.repo.mark_failed(report, self._failure_reason(exc))
            return

        vocabularies = [asdict(v) for v in draft.vocabularies if v.kind != "curious"]
        seen_curious: set[str] = set()
        for item in await self.repo.list_session_curious_words(report.session_id):
            if item["word"] in seen_curious:
                continue
            seen_curious.add(item["word"])
            vocabularies.append(item)

        await self.repo.save_result(
            report,
            speech_summary=draft.speech_summary,
            vocabulary_feedback=draft.vocabulary_feedback,
            expression_patterns=draft.expression_patterns,
            expression_items=[item.model_dump() for item in draft.expression_items],
            logic_items=[item.model_dump() for item in draft.logic_items],
            story_topic_questions=[p.model_dump() for p in draft.story_topic_questions],
            daily_life_questions=[p.model_dump() for p in draft.daily_life_questions],
            vocabularies=vocabularies,
            representative=asdict(draft.representative) if draft.representative else None,
            analyzer_name=draft.analyzer_name,
            report_version=draft.report_version,
        )

    async def _build_draft(self, report: LearningReport):
        session = await self.repo.get_session(report.session_id)
        if session is None:
            raise NotFoundError("학습 세션을 찾을 수 없습니다.")

        messages = await self.repo.list_child_utterances(report.session_id)
        conversation = await self.repo.list_session_messages(report.session_id)
        context = ReportContext(
            story_title=session.story.title,
            child_name=session.child.name,
            utterances=[self._to_utterance_input(message) for message in messages],
            chat_history=self._to_chat_history(conversation),
        )
        return await get_report_analyzer().analyze(context)

    @staticmethod
    def _to_chat_history(messages: list[Message]) -> list[dict]:
        history: list[dict] = []
        for message in messages:
            if not message.text.strip():
                continue
            role = "user" if message.speaker_type == "child" else "AI"
            history.append({"role": role, "content": message.text})
        return history

    @staticmethod
    def _to_utterance_input(message: Message) -> UtteranceInput:
        analysis = message.utterance_analysis
        return UtteranceInput(
            message_id=message.id,
            text=message.text,
            scene_order=message.scene.scene_order,
            turn_order=message.turn_order,
            elements=_element_tags(analysis.detected_elements) if analysis else [],
            child_intent=analysis.child_intent if analysis else None,
            main_point=analysis.main_point if analysis else None,
            utterance_validity=analysis.utterance_validity if analysis else None,
        )

    async def _resolve_session(
        self, parent_id: uuid.UUID, child_id: uuid.UUID, story_id: uuid.UUID
    ) -> StorySession:
        await self._verify_child(parent_id, child_id)
        session = await self.repo.get_latest_completed_session(child_id, story_id)
        if session is None:
            raise NotFoundError("완료된 학습 기록이 없습니다.")
        return session

    async def _verify_child(self, parent_id: uuid.UUID, child_id: uuid.UUID) -> Child:
        child = await self.repo.get_child(child_id)
        if child is None:
            raise NotFoundError("존재하지 않는 자녀 프로필입니다.")
        if child.parent_id != parent_id:
            raise ForbiddenError("접근 권한이 없습니다.")
        return child

    @staticmethod
    def _failure_reason(exc: Exception) -> str:
        return f"{type(exc).__name__}: {exc}"[:_MAX_FAILURE_REASON_LENGTH]

    @staticmethod
    def _curious_item(row: ChildVocabulary) -> VocabularyItem:
        word = row.scene_vocabulary
        return VocabularyItem(
            id=row.id,
            word=word.word,
            kind="curious",
            definition=word.definition,
            example_sentence=word.example_sentence,
            created_at=row.saved_at,
        )

    @staticmethod
    def _to_response(
        report: LearningReport,
        session: StorySession,
        previous_story_id: uuid.UUID | None,
        next_story_id: uuid.UUID | None,
    ) -> ReportResponse:
        return ReportResponse(
            report_id=report.id,
            session_id=report.session_id,
            child_id=report.child_id,
            story_id=report.story_id,
            story_title=session.story.title,
            child_name=session.child.name,
            status=report.status,
            representative=(
                RepresentativeUtterance(
                    message_id=report.representative_message_id,
                    text=report.representative_quote,
                    elements=list(report.representative_elements),
                    reason=report.representative_reason,
                )
                if report.representative_quote
                else None
            ),
            vocabulary=VocabularySection(
                speech_summary=report.speech_summary,
                used_words=[v.word for v in report.vocabularies if v.kind == "used"],
                curious_words=[v.word for v in report.vocabularies if v.kind == "curious"],
                expression_patterns=list(report.expression_patterns),
                feedback=report.vocabulary_feedback,
            ),
            expression=[ReportFeedbackItem(**item) for item in report.expression_items],
            logic=[ReportFeedbackItem(**item) for item in report.logic_items],
            home_conversation=HomeConversationSection(
                story_topics=[ConversationPrompt(**p) for p in report.story_topic_questions],
                daily_life=[ConversationPrompt(**p) for p in report.daily_life_questions],
            ),
            previous_story_id=previous_story_id,
            next_story_id=next_story_id,
            failure_reason=report.failure_reason,
            created_at=report.created_at,
            completed_at=report.completed_at,
        )


async def generate_report_task(report_id: uuid.UUID) -> None:
    """응답 반환 후 실행되므로 요청 스코프 세션을 쓸 수 없다. 자체 세션을 연다."""
    async with AsyncSessionMaker() as db:
        await ReportService(db).run_generation(report_id)


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
