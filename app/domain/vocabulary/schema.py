import uuid

from pydantic import BaseModel, ConfigDict


class VocabularyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    word: str
    story_id: uuid.UUID
    story_title: str
    is_saved: bool


class VocabularyDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    word: str
    definition: str
    usage_context: str
    example_sentence: str
    audio_url: str | None
    story_id: uuid.UUID
    story_title: str
    is_saved: bool
