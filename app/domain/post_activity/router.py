import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession
from app.domain.post_activity.schema import (
    ActivityResponse,
    RetellRequest,
    RetellResponse,
    SubmitRequest,
    SubmitResponse,
)
from app.domain.post_activity.service import PostActivityService

router = APIRouter(prefix="/sessions", tags=["post-activity"])


def _get_service(db: DBSession) -> PostActivityService:
    return PostActivityService(db)


@router.get("/{session_id}/post-activity", response_model=ActivityResponse)
async def get_activity(
    session_id: uuid.UUID,
    user: CurrentUser,
    service: PostActivityService = Depends(_get_service),
):
    return await service.get_activity(session_id, user.id)


@router.post("/{session_id}/post-activity/submit", response_model=SubmitResponse)
async def submit_order(
    session_id: uuid.UUID,
    body: SubmitRequest,
    user: CurrentUser,
    service: PostActivityService = Depends(_get_service),
):
    return await service.submit_order(session_id, user.id, body.submitted_order)


@router.post("/{session_id}/post-activity/retell", response_model=RetellResponse)
async def save_retell(
    session_id: uuid.UUID,
    body: RetellRequest,
    user: CurrentUser,
    service: PostActivityService = Depends(_get_service),
):
    return await service.save_retell(session_id, user.id, body.retelling_text)
