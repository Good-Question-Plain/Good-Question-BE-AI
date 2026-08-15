import uuid
from dataclasses import asdict

from fastapi import BackgroundTasks
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.db.session import AsyncSessionMaker
from app.domain.vocabulary.analyzer import (
    ReportContext,
    UtteranceInput,
    get_report_analyzer,
)
from app.domain.vocabulary.repository import ReportRepository
from app.domain.vocabulary.schema import (
    ConversationPrompt,
    GenerateReportResponse,
    HomeConversationSection,
    ReportFeedbackItem,
    ReportResponse,
    RepresentativeUtterance,
    VocabularyItem,
    VocabularyListResponse,
    VocabularySection,
)
from app.models.child import Child
from app.models.message import Message
from app.models.report import LearningReport
from app.models.story_session import StorySession

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

        if report is None:
            try:
                report = await self.repo.create_generating_report(session)
            except IntegrityError:
                # 동시 요청이 먼저 같은 세션의 리포트를 만든 경우 (session_id UNIQUE)
                raise ConflictError("리포트를 생성하는 중입니다. 잠시 후 다시 확인해주세요.")
        elif report.status == "generating":
            raise ConflictError("리포트를 생성하는 중입니다. 잠시 후 다시 확인해주세요.")
        elif report.status == "completed":
            return GenerateReportResponse(
                report_id=report.id, session_id=session.id, status="completed"
            )
        else:
            report = await self.repo.reset_to_generating(report)

        background_tasks.add_task(generate_report_task, report.id)
        return GenerateReportResponse(
            report_id=report.id, session_id=session.id, status="generating"
        )

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
        total, rows = await self.repo.list_vocabularies(child_id, kind, limit, offset)
        return VocabularyListResponse(
            total=total,
            items=[VocabularyItem.model_validate(row) for row in rows],
        )

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

        await self.repo.save_result(
            report,
            speech_summary=draft.speech_summary,
            vocabulary_feedback=draft.vocabulary_feedback,
            expression_patterns=draft.expression_patterns,
            expression_items=[item.model_dump() for item in draft.expression_items],
            logic_items=[item.model_dump() for item in draft.logic_items],
            story_topic_questions=[p.model_dump() for p in draft.story_topic_questions],
            daily_life_questions=[p.model_dump() for p in draft.daily_life_questions],
            vocabularies=[asdict(v) for v in draft.vocabularies],
            representative=asdict(draft.representative) if draft.representative else None,
            analyzer_name=draft.analyzer_name,
            report_version=draft.report_version,
        )

    async def _build_draft(self, report: LearningReport):
        session = await self.repo.get_session(report.session_id)
        if session is None:
            raise NotFoundError("학습 세션을 찾을 수 없습니다.")

        messages = await self.repo.list_child_utterances(report.session_id)
        context = ReportContext(
            story_title=session.story.title,
            child_name=session.child.name,
            utterances=[self._to_utterance_input(message) for message in messages],
        )
        return await get_report_analyzer().analyze(context)

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
