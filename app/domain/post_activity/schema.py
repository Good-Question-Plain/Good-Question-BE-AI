import uuid

from pydantic import BaseModel


class SceneCard(BaseModel):
    scene_id: uuid.UUID
    title: str
    image_url: str | None


class ActivityResponse(BaseModel):
    attempt_count: int
    is_completed: bool
    cards: list[SceneCard]


class SubmitRequest(BaseModel):
    submitted_order: list[uuid.UUID]


class VocabularyItem(BaseModel):
    word: str
    definition: str


class SubmitResponse(BaseModel):
    is_correct: bool
    attempt_count: int
    vocabulary: list[VocabularyItem] | None = None


class RetellRequest(BaseModel):
    retelling_text: str


class RetellResponse(BaseModel):
    story_title: str
    utterance_count: int
    new_vocabulary_count: int
