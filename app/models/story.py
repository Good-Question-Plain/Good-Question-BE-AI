import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_key: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String, nullable=True)
    difficulty: Mapped[str] = mapped_column(String, nullable=False)
    topics: Mapped[list[str]] = mapped_column(ARRAY(String()), nullable=False)
    estimated_minutes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    post_activity_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    scenes: Mapped[list["StoryScene"]] = relationship(
        back_populates="story",
        order_by="StoryScene.scene_order",
        cascade="all, delete-orphan",
    )
    story_sessions: Mapped[list["StorySession"]] = relationship(back_populates="story")


class StoryScene(Base):
    __tablename__ = "story_scenes"
    __table_args__ = (UniqueConstraint("story_id", "scene_order", name="uq_story_scene_order"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), nullable=False
    )
    content_key: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    scene_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    scene_type: Mapped[str] = mapped_column(String, nullable=False, default="narration")
    scene_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflict: Mapped[str | None] = mapped_column(Text, nullable=True)
    character_key: Mapped[str | None] = mapped_column(String, nullable=True)
    character_name: Mapped[str | None] = mapped_column(String, nullable=True)
    character_opening: Mapped[str | None] = mapped_column(Text, nullable=True)
    character_closing: Mapped[str | None] = mapped_column(Text, nullable=True)
    scene_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_elements: Mapped[list[str] | None] = mapped_column(
        ARRAY(String()), nullable=True
    )
    preferred_turns: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    max_turns: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    mission_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    mission_examples: Mapped[list[str] | None] = mapped_column(
        ARRAY(String()), nullable=True
    )
    scene_title: Mapped[str] = mapped_column(String, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)

    story: Mapped["Story"] = relationship(back_populates="scenes")
    messages: Mapped[list["Message"]] = relationship(back_populates="scene")
    vocabularies: Mapped[list["SceneVocabulary"]] = relationship(
        back_populates="scene", cascade="all, delete-orphan"
    )
