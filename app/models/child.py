import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Child(Base):
    __tablename__ = "children"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    parent: Mapped["Parent"] = relationship(back_populates="children")
    consents: Mapped[list["ChildConsent"]] = relationship(
        back_populates="child", cascade="all, delete-orphan"
    )
    story_sessions: Mapped[list["StorySession"]] = relationship(back_populates="child")
    saved_vocabularies: Mapped[list["ChildVocabulary"]] = relationship(
        back_populates="child", cascade="all, delete-orphan"
    )


class ChildConsent(Base):
    __tablename__ = "child_consents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False
    )
    consent_version: Mapped[str] = mapped_column(String, nullable=False)
    verification_method: Mapped[str] = mapped_column(String, nullable=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    child: Mapped["Child"] = relationship(back_populates="consents")
