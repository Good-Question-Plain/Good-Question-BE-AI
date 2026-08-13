import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SceneVocabulary(Base):
    __tablename__ = "scene_vocabularies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scene_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("story_scenes.id", ondelete="CASCADE"), nullable=False
    )
    word: Mapped[str] = mapped_column(String, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    usage_context: Mapped[str] = mapped_column(Text, nullable=False)
    example_sentence: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(String, nullable=True)

    scene: Mapped["StoryScene"] = relationship(back_populates="vocabularies")
    saved_by: Mapped[list["ChildVocabulary"]] = relationship(
        back_populates="scene_vocabulary", cascade="all, delete-orphan"
    )


class ChildVocabulary(Base):
    __tablename__ = "child_vocabularies"
    __table_args__ = (
        UniqueConstraint("child_id", "scene_vocabulary_id", name="uq_child_scene_vocabulary"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    scene_vocabulary_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scene_vocabularies.id", ondelete="CASCADE"), nullable=False
    )
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    child: Mapped["Child"] = relationship(back_populates="saved_vocabularies")
    scene_vocabulary: Mapped["SceneVocabulary"] = relationship(back_populates="saved_by")
