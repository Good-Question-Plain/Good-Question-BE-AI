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
