import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import BadRequestError, ForbiddenError
from app.models.child import Child
from app.models.post_activity import PostActivityResult
from app.models.story import StoryScene
from app.models.story_session import StorySession
from app.models.vocabulary import SceneVocabulary


def _make_session(status: str = "completed") -> StorySession:
    child = Child(id=uuid.uuid4(), parent_id=uuid.uuid4(), name="지오")
    session = StorySession(
        id=uuid.uuid4(),
        child_id=child.id,
        story_id=uuid.uuid4(),
        status=status,
    )
    session.child = child
    session.story = MagicMock(title="아기돼지 삼형제")
    return session


def _make_scenes(count: int = 5) -> list[StoryScene]:
    scenes = []
    titles = ["가벼운 지푸라기집", "나무로 만든 집", "튼튼한 벽돌집", "늑대가 찾아왔어요", "셋이 함께 안전해요"]
    for i in range(count):
        s = StoryScene(
            id=uuid.uuid4(),
            story_id=uuid.uuid4(),
            scene_order=i + 1,
            scene_title=titles[i],
            scene_description="",
            conflict="",
            character_name="",
            character_opening="",
            character_closing="",
            scene_goal="",
            required_elements=[],
            preferred_turns=2,
            max_turns=4,
        )
        scenes.append(s)
    return scenes


def _make_result(attempt_count: int = 0, is_correct: bool | None = None) -> PostActivityResult:
    r = PostActivityResult(session_id=uuid.uuid4())
    r.attempt_count = attempt_count
    r.is_order_correct = is_correct
    r.retelling_text = None
    r.completed_at = None
    return r


@pytest.fixture
def repo():
    r = MagicMock()
    r.get_session = AsyncMock()
    r.get_or_create_result = AsyncMock()
    r.get_scenes = AsyncMock()
    r.get_vocabulary = AsyncMock()
    r.save_submit = AsyncMock()
    r.save_retell = AsyncMock()
    r.count_child_utterances = AsyncMock(return_value=8)
    r.count_story_vocabulary = AsyncMock(return_value=4)
    return r


@pytest.fixture
def service(repo):
    from app.domain.post_activity.service import PostActivityService
    svc = PostActivityService(AsyncMock())
    svc.repo = repo
    return svc


async def test_get_activity_raises_400_when_session_not_completed(service, repo):
    session = _make_session(status="in_progress")
    repo.get_session.return_value = session

    with pytest.raises(BadRequestError):
        await service.get_activity(uuid.uuid4(), uuid.uuid4())


async def test_get_activity_returns_shuffled_cards(service, repo):
    session = _make_session()
    scenes = _make_scenes(5)
    result = _make_result()
    repo.get_session.return_value = session
    repo.get_or_create_result.return_value = result
    repo.get_scenes.return_value = scenes

    resp = await service.get_activity(session.id, session.child.parent_id)

    assert len(resp.cards) == 5
    assert resp.attempt_count == 0
    assert resp.is_completed is False


async def test_get_activity_is_completed_when_retelling_done(service, repo):
    session = _make_session()
    scenes = _make_scenes(5)
    result = _make_result(attempt_count=1, is_correct=True)
    result.retelling_text = "이야기..."
    result.completed_at = datetime.now(timezone.utc)
    repo.get_session.return_value = session
    repo.get_or_create_result.return_value = result
    repo.get_scenes.return_value = scenes

    resp = await service.get_activity(session.id, session.child.parent_id)

    assert resp.is_completed is True


async def test_submit_raises_400_when_session_not_completed(service, repo):
    session = _make_session(status="in_progress")
    repo.get_session.return_value = session
    repo.get_or_create_result.return_value = _make_result()

    with pytest.raises(BadRequestError):
        await service.submit_order(session.id, uuid.uuid4(), [uuid.uuid4()])


async def test_submit_raises_400_when_already_correct(service, repo):
    session = _make_session()
    result = _make_result(attempt_count=1, is_correct=True)
    repo.get_session.return_value = session
    repo.get_or_create_result.return_value = result

    with pytest.raises(BadRequestError):
        await service.submit_order(session.id, uuid.uuid4(), [uuid.uuid4()])


async def test_submit_raises_400_when_scene_count_mismatch(service, repo):
    session = _make_session()
    scenes = _make_scenes(5)
    result = _make_result()
    repo.get_session.return_value = session
    repo.get_or_create_result.return_value = result
    repo.get_scenes.return_value = scenes

    with pytest.raises(BadRequestError):
        await service.submit_order(session.id, uuid.uuid4(), [uuid.uuid4(), uuid.uuid4()])


async def test_submit_correct_order_returns_vocabulary(service, repo):
    session = _make_session()
    scenes = _make_scenes(5)
    result = _make_result()
    vocab = [SceneVocabulary(id=uuid.uuid4(), scene_id=scenes[0].id, word="용감한", definition="두렵거나 힘들어도 맞서는", usage_context="", example_sentence="")]
    repo.get_session.return_value = session
    repo.get_or_create_result.return_value = result
    repo.get_scenes.return_value = scenes
    repo.get_vocabulary.return_value = vocab
    updated = _make_result(attempt_count=1, is_correct=True)
    repo.save_submit.return_value = updated

    correct_order = [s.id for s in scenes]
    resp = await service.submit_order(session.id, uuid.uuid4(), correct_order)

    assert resp.is_correct is True
    assert resp.vocabulary is not None
    assert resp.vocabulary[0].word == "용감한"


async def test_submit_wrong_order_returns_no_vocabulary(service, repo):
    session = _make_session()
    scenes = _make_scenes(5)
    result = _make_result()
    repo.get_session.return_value = session
    repo.get_or_create_result.return_value = result
    repo.get_scenes.return_value = scenes
    updated = _make_result(attempt_count=1, is_correct=False)
    repo.save_submit.return_value = updated

    wrong_order = [s.id for s in reversed(scenes)]
    resp = await service.submit_order(session.id, uuid.uuid4(), wrong_order)

    assert resp.is_correct is False
    assert resp.vocabulary is None
    repo.get_vocabulary.assert_not_called()


async def test_retell_raises_400_when_quiz_not_solved(service, repo):
    session = _make_session()
    result = _make_result(is_correct=None)
    repo.get_session.return_value = session
    repo.get_or_create_result.return_value = result

    with pytest.raises(BadRequestError):
        await service.save_retell(session.id, uuid.uuid4(), "이야기...")


async def test_retell_returns_summary(service, repo):
    session = _make_session()
    result = _make_result(attempt_count=1, is_correct=True)
    repo.get_session.return_value = session
    repo.get_or_create_result.return_value = result
    repo.save_retell.return_value = result
    repo.count_child_utterances.return_value = 8
    repo.count_story_vocabulary.return_value = 4

    resp = await service.save_retell(session.id, uuid.uuid4(), "이야기...")

    assert resp.story_title == "아기돼지 삼형제"
    assert resp.utterance_count == 8
    assert resp.new_vocabulary_count == 4
