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
import uuid

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import CurrentUser, DBSession, RedisDep
from app.domain.story.schema import (
    SceneItem,
    StoryDetail,
    StoryListItem,
    StoryListResponse,
)
from app.domain.story.service import StoryService

router = APIRouter(prefix="/stories", tags=["stories"])


def _get_service(db: DBSession, redis: RedisDep) -> StoryService:
    return StoryService(db, redis)


@router.get("", response_model=StoryListResponse)
async def get_stories(
    user: CurrentUser,
    category: str | None = Query(None, description="topics 배열과 매칭할 카테고리"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    service: StoryService = Depends(_get_service),
):
    return await service.get_list(category, limit, offset)


# /{story_id} 보다 먼저 선언해야 recommended 가 story_id 로 매칭되지 않는다.
@router.get("/recommended", response_model=list[StoryListItem])
async def get_recommended_stories(
    child_id: uuid.UUID,
    user: CurrentUser,
    service: StoryService = Depends(_get_service),
):
    return await service.get_recommended(user, child_id)


@router.get("/{story_id}", response_model=StoryDetail)
async def get_story(
    story_id: uuid.UUID,
    user: CurrentUser,
    service: StoryService = Depends(_get_service),
):
    return await service.get_detail(story_id)


@router.get("/{story_id}/scenes", response_model=list[SceneItem])
async def get_story_scenes(
    story_id: uuid.UUID,
    user: CurrentUser,
    service: StoryService = Depends(_get_service),
):
    return await service.get_scenes(story_id)
