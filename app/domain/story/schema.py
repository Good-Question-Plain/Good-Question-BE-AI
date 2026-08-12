import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

Difficulty = Literal["쉬움", "보통", "어려움"]


class StoryListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    thumbnail_url: str | None = None
    estimated_minutes: int | None = None
    topics: list[str]
    difficulty: Difficulty


class StoryListResponse(BaseModel):
    items: list[StoryListItem]
    total: int
    limit: int
    offset: int


class StoryDetail(BaseModel):
    id: uuid.UUID
    title: str
    summary: str
    thumbnail_url: str | None = None
    difficulty: Difficulty
    topics: list[str]
    estimated_minutes: int | None = None
    scene_count: int
    characters: list[str]


class SceneItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scene_order: int
    scene_title: str
    scene_type: Literal["narration", "dialogue"]
    scene_description: str | None = None
    character_name: str | None = None
    character_opening: str | None = None
    character_closing: str | None = None
    image_url: str | None = None

import uuid

from pydantic import BaseModel


class StoryListItemResponse(BaseModel):
    id: uuid.UUID
    title: str
    thumbnail_url: str | None
    estimated_minutes: int | None
    topics: list[str]
