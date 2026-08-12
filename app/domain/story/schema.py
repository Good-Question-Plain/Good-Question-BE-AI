import uuid

from pydantic import BaseModel


class StoryListItemResponse(BaseModel):
    id: uuid.UUID
    title: str
    thumbnail_url: str | None
    estimated_minutes: int | None
    topics: list[str]
