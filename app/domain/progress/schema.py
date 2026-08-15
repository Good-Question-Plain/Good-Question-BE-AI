import uuid
from typing import Literal

from pydantic import BaseModel

SceneKind = Literal["narration", "dialogue", "mission"]
SessionStatus = Literal["in_progress", "completed"]
EndReason = Literal["goal_met", "max_turns", "narration_done"]


class MissionPrompt(BaseModel):
    condition: str
    examples: list[str]


class SceneVocabularyItem(BaseModel):
    id: uuid.UUID
    word: str
    definition: str | None = None
    example_sentence: str | None = None
    selected: bool = False


class SceneVocabularyListResponse(BaseModel):
    items: list[SceneVocabularyItem]


class SelectSceneVocabularyRequest(BaseModel):
    scene_vocabulary_id: uuid.UUID


class StepResponse(BaseModel):
    step_index: int
    scene_count: int
    kind: SceneKind
    scene_id: uuid.UUID
    scene_description: str | None = None
    image_url: str | None = None
    character_name: str | None = None  # 한글 표시명. ch_ 슬러그 아님.
    character_opening: str | None = None
    character_closing: str | None = None
    max_turns: int | None = None
    turn: int | None = None
    mission: MissionPrompt | None = None
    vocabularies: list[SceneVocabularyItem] = []


class StartResponse(BaseModel):
    session_id: uuid.UUID
    story_id: uuid.UUID
    status: SessionStatus
    current_step: int
    scene_count: int
    step: StepResponse


class ActiveProgressResponse(BaseModel):
    session_id: uuid.UUID
    story_id: uuid.UUID
    title: str
    thumbnail_url: str | None = None
    current_step: int
    scene_count: int


class ProgressStatusResponse(BaseModel):
    session_id: uuid.UUID
    status: SessionStatus
    current_step: int
    scene_count: int
    current_kind: SceneKind | None = None
    turn: int | None = None
    max_turns: int | None = None


class SpeakResponse(BaseModel):
    accepted: bool
    child_text: str
    character_line: str | None = None
    turn: int
    max_turns: int
    mission: MissionPrompt | None = None
    scene_ended: bool
    end_reason: EndReason | None = None


class CompleteResponse(BaseModel):
    current_step: int
    scene_count: int
    status: SessionStatus
    completed: bool
