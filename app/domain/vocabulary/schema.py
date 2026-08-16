import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ReportStatus = Literal["generating", "completed", "failed"]
VocabularyKind = Literal["used", "curious"]


class ReportFeedbackItem(BaseModel):
    """표현·논리 탭의 항목 하나. PRD 3.6 분석 항목 구조."""

    key: str
    label: str
    description: str
    quotes: list[str] = []
    strength: str | None = None
    tip: str | None = None


class RepresentativeUtterance(BaseModel):
    """리포트를 대표하는 발화 하나. 규칙으로 선정하고 이유 문장은 분석기가 만든다."""

    message_id: uuid.UUID | None = None
    text: str
    elements: list[str] = []
    reason: str | None = None


class ConversationPrompt(BaseModel):
    """집에서 이어가볼 대화 질문 하나."""

    question: str
    practice_label: str


class HomeConversationSection(BaseModel):
    story_topics: list[ConversationPrompt] = []
    daily_life: list[ConversationPrompt] = []


class VocabularySection(BaseModel):
    speech_summary: str | None = None
    used_words: list[str] = []
    curious_words: list[str] = []
    expression_patterns: list[str] = []
    feedback: str | None = None


class GenerateReportResponse(BaseModel):
    report_id: uuid.UUID
    session_id: uuid.UUID
    status: ReportStatus


class ReportResponse(BaseModel):
    report_id: uuid.UUID
    session_id: uuid.UUID
    child_id: uuid.UUID
    story_id: uuid.UUID
    story_title: str
    child_name: str
    status: ReportStatus
    representative: RepresentativeUtterance | None = None
    vocabulary: VocabularySection
    expression: list[ReportFeedbackItem] = []
    logic: list[ReportFeedbackItem] = []
    home_conversation: HomeConversationSection
    previous_story_id: uuid.UUID | None = None
    next_story_id: uuid.UUID | None = None
    failure_reason: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class VocabularyItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    word: str
    kind: VocabularyKind
    definition: str | None = None
    example_sentence: str | None = None
    created_at: datetime


class VocabularyListResponse(BaseModel):
    total: int
    items: list[VocabularyItem]


class VocabularyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    word: str
    story_id: uuid.UUID
    story_title: str
    is_saved: bool


class VocabularyDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    word: str
    definition: str
    usage_context: str
    example_sentence: str
    audio_url: str | None
    story_id: uuid.UUID
    story_title: str
    is_saved: bool
