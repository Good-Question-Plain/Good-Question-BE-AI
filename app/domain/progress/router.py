import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile

from app.core.dependencies import CurrentUser, DBSession, RedisDep
from app.core.exceptions import BadRequestError
from app.domain.progress.schema import (
    ActiveProgressResponse,
    CompleteResponse,
    ProgressStatusResponse,
    SceneVocabularyListResponse,
    SelectSceneVocabularyRequest,
    SpeakResponse,
    StartResponse,
    StepResponse,
)
from app.domain.progress.service import ProgressService

router = APIRouter(prefix="/progress", tags=["progress"])


def _get_service(db: DBSession, redis: RedisDep) -> ProgressService:
    return ProgressService(db, redis)


@router.get("/active", response_model=ActiveProgressResponse | None)
async def get_active_progress(
    child_id: uuid.UUID,
    user: CurrentUser,
    service: ProgressService = Depends(_get_service),
):
    return await service.get_active(user, child_id)


@router.post("/{story_id}/start", response_model=StartResponse)
async def start_story(
    story_id: uuid.UUID,
    child_id: uuid.UUID,
    user: CurrentUser,
    service: ProgressService = Depends(_get_service),
):
    return await service.start(user, child_id, story_id)


@router.get("/{story_id}", response_model=ProgressStatusResponse)
async def get_progress(
    story_id: uuid.UUID,
    child_id: uuid.UUID,
    user: CurrentUser,
    service: ProgressService = Depends(_get_service),
):
    return await service.get_status(user, child_id, story_id)


@router.post("/{story_id}/steps/{step_index}", response_model=StepResponse)
async def enter_step(
    story_id: uuid.UUID,
    step_index: int,
    child_id: uuid.UUID,
    user: CurrentUser,
    service: ProgressService = Depends(_get_service),
):
    if step_index < 1:
        raise BadRequestError("단계 번호는 1 이상이어야 합니다.")
    return await service.enter_step(user, child_id, story_id, step_index)


@router.post(
    "/{story_id}/steps/{step_index}/speak",
    response_model=SpeakResponse,
)
async def speak(
    story_id: uuid.UUID,
    step_index: int,
    child_id: uuid.UUID,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(..., description="아이 음성 (m4a)"),
    service: ProgressService = Depends(_get_service),
):
    data = await audio.read()
    if not data:
        raise BadRequestError("오디오 파일이 비어 있습니다.")
    return await service.speak(
        user, child_id, story_id, step_index, data, background_tasks
    )


@router.post(
    "/{story_id}/steps/{step_index}/complete",
    response_model=CompleteResponse,
)
async def complete_step(
    story_id: uuid.UUID,
    step_index: int,
    child_id: uuid.UUID,
    user: CurrentUser,
    background_tasks: BackgroundTasks,
    service: ProgressService = Depends(_get_service),
):
    return await service.complete(
        user, child_id, story_id, step_index, background_tasks
    )


@router.post(
    "/{story_id}/steps/{step_index}/vocabularies",
    response_model=SceneVocabularyListResponse,
)
async def select_step_vocabulary(
    story_id: uuid.UUID,
    step_index: int,
    child_id: uuid.UUID,
    body: SelectSceneVocabularyRequest,
    user: CurrentUser,
    service: ProgressService = Depends(_get_service),
):
    if step_index < 1:
        raise BadRequestError("단계 번호는 1 이상이어야 합니다.")
    return await service.select_scene_vocabulary(
        user, child_id, story_id, step_index, body.scene_vocabulary_id
    )


@router.delete(
    "/{story_id}/steps/{step_index}/vocabularies/{scene_vocabulary_id}",
    response_model=SceneVocabularyListResponse,
)
async def unselect_step_vocabulary(
    story_id: uuid.UUID,
    step_index: int,
    scene_vocabulary_id: uuid.UUID,
    child_id: uuid.UUID,
    user: CurrentUser,
    service: ProgressService = Depends(_get_service),
):
    if step_index < 1:
        raise BadRequestError("단계 번호는 1 이상이어야 합니다.")
    return await service.unselect_scene_vocabulary(
        user, child_id, story_id, step_index, scene_vocabulary_id
    )
