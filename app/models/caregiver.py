import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SocialProvider(str, enum.Enum):
    email = "email"
    kakao = "kakao"
    google = "google"
    naver = "naver"


class Caregiver(Base):
    __tablename__ = "caregiver"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    social_provider: Mapped[SocialProvider] = mapped_column(
        SAEnum(SocialProvider), nullable=False, default=SocialProvider.email
    )
    social_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
