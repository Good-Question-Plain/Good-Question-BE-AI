import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession, S3ClientDep
from app.domain.main.schema import MainPageResponse
from app.domain.main.service import MainService

router = APIRouter(prefix="/main", tags=["main"])

def _get_service(db: DBSession, s3: S3ClientDep) -> MainService:
    return MainService(db, s3)


@router.get("", response_model=MainPageResponse)
async def get_main_page(
    child_id: uuid.UUID,
    user: CurrentUser,
    service: MainService = Depends(_get_service),
):
    return await service.get_main_page(child_id)
