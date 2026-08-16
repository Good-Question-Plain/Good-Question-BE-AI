import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.core.dependencies import CurrentUser, DBSession
from app.domain.vocabulary.schema import (
    GenerateReportResponse,
    ReportResponse,
    VocabularyDetail,
    VocabularyKind,
    VocabularyListItem,
    VocabularyListResponse,
)
from app.domain.vocabulary.service import ReportService, VocabularyService

reports_router = APIRouter(prefix="/reports", tags=["reports"])
vocabulary_router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


def _get_report_service(db: DBSession) -> ReportService:
    return ReportService(db)


def _get_vocabulary_service(db: DBSession) -> VocabularyService:
    return VocabularyService(db)


@reports_router.post(
    "/{story_id}/generate",
    response_model=GenerateReportResponse,
    status_code=202,
)
async def generate_report(
    story_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    child_id: uuid.UUID = Query(..., description="리포트를 생성할 자녀 프로필 ID"),
    service: ReportService = Depends(_get_report_service),
):
    return await service.request_generation(user.id, child_id, story_id, background_tasks)


@reports_router.get("/{story_id}", response_model=ReportResponse)
async def get_report(
    story_id: uuid.UUID,
    user: CurrentUser,
    child_id: uuid.UUID = Query(..., description="리포트를 조회할 자녀 프로필 ID"),
    service: ReportService = Depends(_get_report_service),
):
    return await service.get_report(user.id, child_id, story_id)


@vocabulary_router.get("", response_model=VocabularyListResponse)
async def list_vocabulary(
    user: CurrentUser,
    child_id: uuid.UUID = Query(..., description="어휘를 조회할 자녀 프로필 ID"),
    kind: VocabularyKind | None = Query(None, description="used=사용한 어휘, curious=궁금해한 어휘"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: ReportService = Depends(_get_report_service),
):
    return await service.list_vocabulary(user.id, child_id, kind, limit, offset)


@vocabulary_router.get("/saved", response_model=list[VocabularyListItem])
async def get_saved_vocabulary_list(
    child_id: uuid.UUID,
    user: CurrentUser,
    story_id: uuid.UUID | None = None,
    service: VocabularyService = Depends(_get_vocabulary_service),
):
    return await service.get_list(user, child_id, story_id)


@vocabulary_router.get("/{vocab_id}", response_model=VocabularyDetail)
async def get_vocabulary_detail(
    vocab_id: uuid.UUID,
    child_id: uuid.UUID,
    user: CurrentUser,
    service: VocabularyService = Depends(_get_vocabulary_service),
):
    return await service.get_detail(user, child_id, vocab_id)


@vocabulary_router.post("/{vocab_id}/save", status_code=204)
async def save_word(
    vocab_id: uuid.UUID,
    child_id: uuid.UUID,
    user: CurrentUser,
    service: VocabularyService = Depends(_get_vocabulary_service),
):
    await service.save_word(user, child_id, vocab_id)


@vocabulary_router.delete("/{vocab_id}/save", status_code=204)
async def unsave_word(
    vocab_id: uuid.UUID,
    child_id: uuid.UUID,
    user: CurrentUser,
    service: VocabularyService = Depends(_get_vocabulary_service),
):
    await service.unsave_word(user, child_id, vocab_id)
