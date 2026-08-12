from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession
from app.domain.story.schema import StoryListItemResponse
from app.domain.story.service import StoryService

router = APIRouter(prefix="/stories", tags=["stories"])


def _get_service(db: DBSession) -> StoryService:
    return StoryService(db)


@router.get("", response_model=list[StoryListItemResponse])
async def list_stories(
    user: CurrentUser,
    topic: str | None = None,
    service: StoryService = Depends(_get_service),
):
    return await service.list_stories(topic)
