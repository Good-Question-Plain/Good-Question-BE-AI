import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError
from app.domain.auth.repository import ParentRepository
from app.models.parent import Parent


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ParentRepository(db)

    async def sync_profile(self, user_id: str, name: str) -> None:
        if await self.repo.get_by_id(user_id):
            raise ConflictError("이미 프로필이 등록된 사용자입니다.")
        await self.repo.create(parent_id=user_id, name=name)

    async def delete_account(self, parent: Parent) -> None:
        await self._delete_supabase_user(str(parent.id))
        await self.repo.delete(parent)

    async def _delete_supabase_user(self, user_id: str) -> None:
        url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}"
        headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=headers)
            if resp.status_code not in (200, 204, 404):
                raise BadRequestError("Supabase 계정 삭제에 실패했습니다.")
