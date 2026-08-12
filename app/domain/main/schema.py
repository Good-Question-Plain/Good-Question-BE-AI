import uuid

from pydantic import BaseModel

class ContinueStoryResponse(BaseModel):
    story_id: uuid.UUID
    title: str
    thumbnail_url: str | None
    progress_percentage: int


class RecommendedStoryResponse(BaseModel):
    id: uuid.UUID
    title: str
    thumbnail_url: str | None
    estimated_minutes: int | None
    topics: list[str]


class MainPageResponse(BaseModel):
    continue_story: ContinueStoryResponse | None
    recommended_stories: list[RecommendedStoryResponse]
