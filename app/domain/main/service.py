import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.main.repository import MainRepository
from app.domain.main.schema import (ContinueStoryResponse, MainPageResponse, RecommendedStoryResponse, )
from app.domain.story.repository import StoryRepository
_RECOMMENDED_LIMIT = 3

class MainService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = MainRepository(db)
        self.story_repo = StoryRepository(db)

    async def get_main_page(self, child_id: uuid.UUID) -> MainPageResponse:
        continue_story = await self._build_continue_story(child_id)
        popular_stories = await self.story_repo.get_popular_stories(_RECOMMENDED_LIMIT)
        recommended_stories = [
            RecommendedStoryResponse(
                id=story.id,
                title=story.title,
                thumbnail_url=story.thumbnail_url,
                estimated_minutes=story.estimated_minutes,
                topics=story.topics,
            )
            for story in popular_stories
        ]
        return MainPageResponse(
            continue_story=continue_story,
            recommended_stories=recommended_stories,
        )

    async def _build_continue_story(self, child_id: uuid.UUID) -> ContinueStoryResponse | None:
        session = await self.repo.get_active_session(child_id)
        if not session:
            return None

        total_scenes = await self.story_repo.count_scenes(session.story_id)
        current_order = session.current_scene.scene_order if session.current_scene else 1
        completed_scene_order = max(current_order - 1, 0)
        progress_percentage = (
            round(completed_scene_order / total_scenes * 100) if total_scenes else 0
        )

        return ContinueStoryResponse(
            story_id=session.story_id,
            title=session.story.title,
            thumbnail_url=session.story.thumbnail_url,
            progress_percentage=progress_percentage,
        )
