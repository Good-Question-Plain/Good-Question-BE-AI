import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession
from app.domain.vocabulary.schema import VocabularyDetail, VocabularyListItem
from app.domain.vocabulary.service import VocabularyService

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


def _get_service(db: DBSession) -> VocabularyService:
    return VocabularyService(db)


@router.get("", response_model=list[VocabularyListItem])
async def get_vocabulary_list(
    child_id: uuid.UUID,
    user: CurrentUser,
    story_id: uuid.UUID | None = None,
    service: VocabularyService = Depends(_get_service),
):
    return await service.get_list(user, child_id, story_id)


@router.get("/{vocab_id}", response_model=VocabularyDetail)
async def get_vocabulary_detail(
    vocab_id: uuid.UUID,
    child_id: uuid.UUID,
    user: CurrentUser,
    service: VocabularyService = Depends(_get_service),
):
    return await service.get_detail(user, child_id, vocab_id)


@router.post("/{vocab_id}/save", status_code=204)
async def save_word(
    vocab_id: uuid.UUID,
    child_id: uuid.UUID,
    user: CurrentUser,
    service: VocabularyService = Depends(_get_service),
):
    await service.save_word(user, child_id, vocab_id)


@router.delete("/{vocab_id}/save", status_code=204)
async def unsave_word(
    vocab_id: uuid.UUID,
    child_id: uuid.UUID,
    user: CurrentUser,
    service: VocabularyService = Depends(_get_service),
):
    await service.unsave_word(user, child_id, vocab_id)
