import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LearningReport(Base):
    __tablename__ = "learning_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("story_sessions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    story_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stories.id"), nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False, default="generating")

    # 어휘 탭
    speech_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    vocabulary_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    expression_patterns: Mapped[list[str]] = mapped_column(
        ARRAY(String()), nullable=False, default=list
    )

    # 표현 탭 / 논리 탭 — ReportFeedbackItem 구조의 리스트
    expression_items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    logic_items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # "집에서 이어가볼까요?" — {question, practice_label} 구조의 리스트
    story_topic_questions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    daily_life_questions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # 대표 발화 — 규칙 기반 선정 + 분석기가 만든 선정 이유
    representative_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
    representative_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    representative_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    representative_elements: Mapped[list[str]] = mapped_column(
        ARRAY(String()), nullable=False, default=list
    )

    analyzer_name: Mapped[str | None] = mapped_column(String, nullable=True)
    report_version: Mapped[str] = mapped_column(String, nullable=False, default="stub_v1")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["StorySession"] = relationship(back_populates="learning_report")
    vocabularies: Mapped[list["ReportVocabulary"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class ReportVocabulary(Base):
    __tablename__ = "report_vocabularies"
    __table_args__ = (
        UniqueConstraint("report_id", "word", "kind", name="uq_report_vocabulary_word"),
        Index("ix_report_vocabularies_child_kind", "child_id", "kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("learning_reports.id", ondelete="CASCADE"), nullable=False
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    word: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_sentence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    report: Mapped["LearningReport"] = relationship(back_populates="vocabularies")
