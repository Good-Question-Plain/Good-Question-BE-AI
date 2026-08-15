import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StorySession(Base):
    __tablename__ = "story_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), nullable=False
    )
    current_scene_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("story_scenes.id", ondelete="SET NULL"), nullable=True
    )

    # 장면 내 상태 — 장면 전환 시 초기화 대상
    current_child_turn_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    accumulated_elements: Mapped[list[str]] = mapped_column(ARRAY(String()), nullable=False, default=list)
    last_detected_elements: Mapped[list[str]] = mapped_column(ARRAY(String()), nullable=False, default=list)
    last_response_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    last_guidance_target: Mapped[str | None] = mapped_column(String, nullable=True)
    turns_without_new_element: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    consecutive_low_information_turns: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    scene_goal_met: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scene_end_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    # 세션 전체 상태
    status: Mapped[str] = mapped_column(String, nullable=False, default="in_progress")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    child: Mapped["Child"] = relationship(back_populates="story_sessions")
    story: Mapped["Story"] = relationship(back_populates="story_sessions")
    current_scene: Mapped["StoryScene | None"] = relationship(
        foreign_keys=[current_scene_id]
    )
    messages: Mapped[list["Message"]] = relationship(back_populates="session")
    post_activity_result: Mapped["PostActivityResult | None"] = relationship(
        back_populates="session"
    )
    learning_report: Mapped["LearningReport | None"] = relationship(back_populates="session")
    child_vocabularies: Mapped[list["ChildVocabulary"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
