import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("story_sessions.id", ondelete="CASCADE"), nullable=False
    )
    scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("story_scenes.id", ondelete="CASCADE"), nullable=False
    )
    speaker_type: Mapped[str] = mapped_column(String, nullable=False)
    turn_order: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    stt_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session: Mapped["StorySession"] = relationship(back_populates="messages")
    scene: Mapped["StoryScene"] = relationship(back_populates="messages")
    utterance_analysis: Mapped["UtteranceAnalysis | None"] = relationship(
        back_populates="message"
    )


class UtteranceAnalysis(Base):
    __tablename__ = "utterance_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    child_intent: Mapped[str | None] = mapped_column(String, nullable=True)
    main_point: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_elements: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    utterance_validity: Mapped[str] = mapped_column(String, nullable=False)
    analysis_version: Mapped[str] = mapped_column(String, nullable=False, default="mvp_v1")

    message: Mapped["Message"] = relationship(back_populates="utterance_analysis")
