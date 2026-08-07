import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.caregiver import Caregiver, SocialProvider


class CaregiverRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> Caregiver | None:
        result = await self.db.execute(select(Caregiver).where(Caregiver.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, caregiver_id: str) -> Caregiver | None:
        result = await self.db.execute(
            select(Caregiver).where(Caregiver.id == uuid.UUID(caregiver_id))
        )
        return result.scalar_one_or_none()

    async def get_by_social(self, provider: SocialProvider, social_id: str) -> Caregiver | None:
        result = await self.db.execute(
            select(Caregiver).where(
                Caregiver.social_provider == provider,
                Caregiver.social_id == social_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        hashed_password: str | None = None,
        social_provider: SocialProvider = SocialProvider.email,
        social_id: str | None = None,
        is_verified: bool = False,
    ) -> Caregiver:
        caregiver = Caregiver(
            email=email,
            hashed_password=hashed_password,
            social_provider=social_provider,
            social_id=social_id,
            is_verified=is_verified,
        )
        self.db.add(caregiver)
        await self.db.commit()
        await self.db.refresh(caregiver)
        return caregiver

    async def set_verified(self, caregiver: Caregiver) -> None:
        caregiver.is_verified = True
        await self.db.commit()
