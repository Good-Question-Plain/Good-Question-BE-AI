import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PostActivityResult(Base):
    __tablename__ = "post_activity_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("story_sessions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    submitted_order: Mapped[list[str] | None] = mapped_column(ARRAY(String()), nullable=True)
    is_order_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    attempt_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    retelling_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["StorySession"] = relationship(back_populates="post_activity_result")
