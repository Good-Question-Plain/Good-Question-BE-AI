from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.story.repository import StoryRepository
from app.domain.story.schema import StoryListItemResponse


class StoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = StoryRepository(db)

    async def list_stories(self, topic: str | None) -> list[StoryListItemResponse]:
        stories = await self.repo.list_stories(topic)
        return [
            StoryListItemResponse(
                id=story.id,
                title=story.title,
                thumbnail_url=story.thumbnail_url,
                estimated_minutes=story.estimated_minutes,
                topics=story.topics,
            )
            for story in stories
        ]

import uuid

from pydantic import TypeAdapter
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.domain.story.character import scene_character_name
from app.domain.story.repository import StoryRepository
from app.domain.story.schema import (
    SceneItem,
    StoryDetail,
    StoryListItem,
    StoryListResponse,
)
from app.models.child import Child
from app.models.parent import Parent
from app.models.story import Story

RECOMMENDED_COUNT = 3

_STORY_TTL_SECONDS = 3600
_RECOMMENDED_TTL_SECONDS = 600

_story_list_adapter = TypeAdapter(list[StoryListItem])
_scene_list_adapter = TypeAdapter(list[SceneItem])


class StoryService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.repo = StoryRepository(db)
        self.db = db
        self.redis = redis

    async def _verify_child_ownership(self, parent: Parent, child_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(Child).where(Child.id == child_id, Child.parent_id == parent.id)
        )
        if result.scalar_one_or_none() is None:
            raise ForbiddenError("해당 자녀 프로필에 접근할 수 없습니다.")

    async def get_list(
        self,
        category: str | None,
        limit: int,
        offset: int,
    ) -> StoryListResponse:
        stories, total = await self.repo.list_published(category, limit, offset)
        return StoryListResponse(
            items=[StoryListItem.model_validate(s) for s in stories],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_recommended(
        self, parent: Parent, child_id: uuid.UUID
    ) -> list[StoryListItem]:
        await self._verify_child_ownership(parent, child_id)

        key = f"recommended:child:{child_id}"
        cached = await self.redis.get(key)
        if cached is not None:
            return _story_list_adapter.validate_json(cached)

        stories = await self.repo.list_recommended(child_id, RECOMMENDED_COUNT)
        items = [StoryListItem.model_validate(s) for s in stories]
        await self.redis.set(
            key, _story_list_adapter.dump_json(items), ex=_RECOMMENDED_TTL_SECONDS
        )
        return items

    async def get_detail(self, story_id: uuid.UUID) -> StoryDetail:
        key = f"story:{story_id}"
        cached = await self.redis.get(key)
        if cached is not None:
            return StoryDetail.model_validate_json(cached)

        story = await self._get_published(story_id)
        detail = StoryDetail(
            id=story.id,
            title=story.title,
            summary=story.summary,
            thumbnail_url=story.thumbnail_url,
            difficulty=story.difficulty,
            topics=story.topics,
            estimated_minutes=story.estimated_minutes,
            scene_count=len(story.scenes),
            characters=list(
                dict.fromkeys(
                    name
                    for s in story.scenes
                    if (name := scene_character_name(s))
                )
            ),
        )
        await self.redis.set(key, detail.model_dump_json(), ex=_STORY_TTL_SECONDS)
        return detail

    async def get_scenes(self, story_id: uuid.UUID) -> list[SceneItem]:
        key = f"story:{story_id}:scenes"
        cached = await self.redis.get(key)
        if cached is not None:
            return _scene_list_adapter.validate_json(cached)

        story = await self._get_published(story_id)
        scenes = [
            SceneItem(
                id=s.id,
                scene_order=s.scene_order,
                scene_title=s.scene_title,
                scene_type=s.scene_type,  # type: ignore[arg-type]
                scene_description=s.scene_description,
                character_name=scene_character_name(s),
                character_opening=s.character_opening,
                character_closing=s.character_closing,
                image_url=s.image_url,
            )
            for s in story.scenes
        ]
        await self.redis.set(
            key, _scene_list_adapter.dump_json(scenes), ex=_STORY_TTL_SECONDS
        )
        return scenes

    async def _get_published(self, story_id: uuid.UUID) -> Story:
        story = await self.repo.get_published_with_scenes(story_id)
        if story is None:
            raise NotFoundError("스토리를 찾을 수 없습니다.")
        return story
