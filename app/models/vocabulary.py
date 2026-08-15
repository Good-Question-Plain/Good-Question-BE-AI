import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SceneVocabulary(Base):
    __tablename__ = "scene_vocabularies"
    __table_args__ = (
        UniqueConstraint("scene_id", "word", name="uq_scene_vocabulary_word"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("story_scenes.id", ondelete="CASCADE"), nullable=False
    )
    word: Mapped[str] = mapped_column(String, nullable=False)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_sentence: Mapped[str | None] = mapped_column(Text, nullable=True)

    scene: Mapped["StoryScene"] = relationship(back_populates="vocabularies")
    selections: Mapped[list["ChildVocabulary"]] = relationship(
        back_populates="scene_vocabulary", cascade="all, delete-orphan"
    )


class ChildVocabulary(Base):
    __tablename__ = "child_vocabularies"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "scene_vocabulary_id",
            name="uq_child_vocabulary_session_word",
        ),
        Index("ix_child_vocabularies_child_id", "child_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("story_sessions.id", ondelete="CASCADE"), nullable=False
    )
    scene_vocabulary_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scene_vocabularies.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String, nullable=False, default="curious")
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    scene_vocabulary: Mapped["SceneVocabulary"] = relationship(back_populates="selections")
    session: Mapped["StorySession"] = relationship(back_populates="child_vocabularies")
