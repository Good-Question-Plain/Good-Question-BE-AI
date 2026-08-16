import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.domain.auth.repository import ParentRepository
from app.models.parent import Parent

_SUPABASE_HEADERS = {
    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ParentRepository(db)

    async def sync_profile(self, user_id: str, name: str) -> None:
        if await self.repo.get_by_id(user_id):
            raise ConflictError("이미 프로필이 등록된 사용자입니다.")
        await self.repo.create(parent_id=user_id, name=name)

    async def verify_password(self, email: str, password: str) -> None:
        url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers=_SUPABASE_HEADERS,
                json={"email": email, "password": password},
            )
        if resp.status_code != 200:
            raise UnauthorizedError("비밀번호가 올바르지 않습니다.")

    async def change_password(
        self, user_id: str, email: str, current_password: str, new_password: str
    ) -> None:
        await self.verify_password(email, current_password)
        await self._update_supabase_password(user_id, new_password)

    async def delete_account(self, parent: Parent) -> None:
        await self._delete_supabase_user(str(parent.id))
        await self.repo.delete(parent)

    async def _update_supabase_password(self, user_id: str, new_password: str) -> None:
        url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                url, headers=_SUPABASE_HEADERS, json={"password": new_password}
            )
        if resp.status_code not in (200, 201):
            raise BadRequestError("비밀번호 변경에 실패했습니다.")

    async def _delete_supabase_user(self, user_id: str) -> None:
        url = f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=_SUPABASE_HEADERS)
            if resp.status_code not in (200, 204, 404):
                raise BadRequestError("Supabase 계정 삭제에 실패했습니다.")
