# Post-Activity Quiz Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 스토리 세션 완료 후 씬 순서 맞추기 퀴즈 → 리텔링 → 완성 화면 데이터 반환 API 구현

**Architecture:** `app/domain/post_activity/` 독립 도메인 신설. `StoryScene`에 `scene_title` 컬럼 추가. 기존 `PostActivityResult` 모델을 활용해 결과 저장.

**Tech Stack:** FastAPI, SQLAlchemy 2.x async, PostgreSQL, Alembic, pytest + AsyncMock

**Spec:** `docs/superpowers/specs/2026-08-14-post-activity-quiz-design.md`

## Global Constraints

- Python 3.14, async/await everywhere
- SQLAlchemy 2.x AsyncSession only (no sync queries)
- uv for dependencies — do not use pip
- All new domain files follow `router → service → repository` layered pattern
- `CurrentUser` = `Parent` object from `app.core.dependencies`
- Error classes: `BadRequestError(400)`, `ForbiddenError(403)`, `NotFoundError(404)` from `app.core.exceptions`
- 테스트는 mock 기반 (DB 없이), `pytest-asyncio` `asyncio_mode = "auto"`
- 브랜치: `feature/post-activity-quiz`

---

## File Map

| 파일 | 역할 |
|------|------|
| `app/models/story.py` | `scene_title` 컬럼 추가 |
| `alembic/versions/008_add_scene_title_to_story_scenes.py` | scene_title 마이그레이션 |
| `alembic/versions/009_seed_mock_story_three_little_pigs.py` | mock 데이터 시드 |
| `app/domain/post_activity/__init__.py` | 빈 파일 |
| `app/domain/post_activity/schema.py` | Pydantic 요청/응답 스키마 |
| `app/domain/post_activity/repository.py` | DB 접근 전담 |
| `app/domain/post_activity/service.py` | 비즈니스 로직 |
| `app/domain/post_activity/router.py` | FastAPI 라우터 |
| `main.py` | 라우터 등록 |
| `tests/domain/post_activity/__init__.py` | 빈 파일 |
| `tests/domain/post_activity/test_service.py` | service 단위 테스트 |
| `tests/domain/post_activity/test_schema.py` | schema 유효성 테스트 |

---

### Task 1: StoryScene 모델에 scene_title 추가 + 마이그레이션

**Files:**
- Modify: `app/models/story.py`
- Create: `alembic/versions/008_add_scene_title_to_story_scenes.py`

**Interfaces:**
- Produces: `StoryScene.scene_title: str` — Task 3, 4에서 사용

- [ ] **Step 1: `app/models/story.py`에 `scene_title` 컬럼 추가**

`StoryScene` 클래스 내 `image_url` 바로 위에 삽입:

```python
scene_title: Mapped[str] = mapped_column(String, nullable=False)
```

- [ ] **Step 2: 마이그레이션 파일 생성**

`alembic/versions/008_add_scene_title_to_story_scenes.py`:

```python
"""add scene_title to story_scenes

Revision ID: 008
Revises: 007
Create Date: 2026-08-14
"""

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "story_scenes",
        sa.Column("scene_title", sa.String(), nullable=False, server_default=""),
    )
    op.alter_column("story_scenes", "scene_title", server_default=None)


def downgrade() -> None:
    op.drop_column("story_scenes", "scene_title")
```

- [ ] **Step 3: 마이그레이션 실행 확인**

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic current
```

Expected: `008 (head)` 출력

- [ ] **Step 4: Commit**

```bash
git add app/models/story.py alembic/versions/008_add_scene_title_to_story_scenes.py
git commit -m "feat: add scene_title column to story_scenes"
```

---

### Task 2: Mock 데이터 시드 (아기돼지 삼형제)

**Files:**
- Create: `alembic/versions/009_seed_mock_story_three_little_pigs.py`

**Interfaces:**
- Produces: stories, story_scenes, scene_vocabularies 테이블에 mock 행 삽입

- [ ] **Step 1: 시드 마이그레이션 파일 생성**

`alembic/versions/009_seed_mock_story_three_little_pigs.py`:

```python
"""seed mock story: 아기돼지 삼형제

Revision ID: 009
Revises: 008
Create Date: 2026-08-14
"""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

STORY_ID = "11111111-1111-1111-1111-111111111111"
SCENE_IDS = [
    "21111111-1111-1111-1111-111111111111",  # 가벼운 지푸라기집
    "21111111-1111-1111-1111-111111111112",  # 나무로 만든 집
    "21111111-1111-1111-1111-111111111113",  # 튼튼한 벽돌집
    "21111111-1111-1111-1111-111111111114",  # 늑대가 찾아왔어요
    "21111111-1111-1111-1111-111111111115",  # 셋이 함께 안전해요
]
VOCAB_IDS = [
    "31111111-1111-1111-1111-111111111111",  # 용감한
    "31111111-1111-1111-1111-111111111112",  # 친구
    "31111111-1111-1111-1111-111111111113",  # 숲
    "31111111-1111-1111-1111-111111111114",  # 모험
]


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text("""
            INSERT INTO stories (id, title, summary, difficulty, topics, estimated_minutes, status)
            VALUES (
                :id, :title, :summary, :difficulty,
                ARRAY['우정','용기','협력'],
                :estimated_minutes, :status
            )
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id": STORY_ID,
            "title": "아기돼지 삼형제",
            "summary": "세 마리 아기돼지가 각자 집을 짓고, 무서운 늑대로부터 힘을 합쳐 안전하게 지내는 이야기입니다.",
            "difficulty": "easy",
            "estimated_minutes": 15,
            "status": "published",
        },
    )

    scenes = [
        (SCENE_IDS[0], 1, "가벼운 지푸라기집", "첫째 아기돼지", "첫째 돼지는 빨리 놀고 싶어서 지푸라기로 가볍게 집을 지었습니다.", "지푸라기집을 짓는 이유를 이해하고 공감하는 대화를 나눈다"),
        (SCENE_IDS[1], 2, "나무로 만든 집", "둘째 아기돼지", "둘째 돼지는 나뭇가지로 집을 지었습니다. 빠르게 짓고 싶었지만 조금 더 튼튼하게 만들었습니다.", "나무집을 짓는 결정에 대해 이야기한다"),
        (SCENE_IDS[2], 3, "튼튼한 벽돌집", "셋째 아기돼지", "셋째 돼지는 시간이 걸려도 튼튼한 벽돌집을 지었습니다. 형들은 놀러 가도 셋째는 열심히 집을 지었습니다.", "튼튼한 집을 짓는 것의 중요성을 이야기한다"),
        (SCENE_IDS[3], 4, "늑대가 찾아왔어요", "늑대", "무서운 늑대가 나타나 입으로 훅 불어서 지푸라기집과 나무집을 무너뜨렸습니다.", "늑대가 왔을 때의 두려움과 대처를 이야기한다"),
        (SCENE_IDS[4], 5, "셋이 함께 안전해요", "셋째 아기돼지", "세 형제가 모두 벽돌집으로 모여 함께 안전하게 지냈습니다. 늑대는 벽돌집을 무너뜨리지 못했습니다.", "함께 힘을 합치는 것의 중요성을 이야기한다"),
    ]

    for scene_id, order, title, char_name, description, goal in scenes:
        conn.execute(
            sa.text("""
                INSERT INTO story_scenes (
                    id, story_id, scene_order, scene_title, scene_description,
                    conflict, character_name, character_opening, character_closing,
                    scene_goal, required_elements, preferred_turns, max_turns
                )
                VALUES (
                    :id, :story_id, :order, :title, :description,
                    '', :char_name, '', '',
                    :goal, ARRAY[]::text[], 2, 4
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": scene_id,
                "story_id": STORY_ID,
                "order": order,
                "title": title,
                "description": description,
                "char_name": char_name,
                "goal": goal,
            },
        )

    vocabs = [
        (VOCAB_IDS[0], SCENE_IDS[0], "용감한", "두렵거나 힘들어도 포기하지 않고 맞서는", "위험한 상황에서도 용감하게 행동할 때", "아기돼지는 용감하게 늑대에 맞섰어요."),
        (VOCAB_IDS[1], SCENE_IDS[1], "친구", "서로 마음이 맞아 가깝게 지내는 사람", "함께 도움을 주고받는 관계를 표현할 때", "세 형제는 서로의 친구이자 가족이에요."),
        (VOCAB_IDS[2], SCENE_IDS[2], "숲", "나무가 많이 우거진 곳", "아기돼지들이 사는 배경을 묘사할 때", "아기돼지 형제는 숲 속에 각자 집을 지었어요."),
        (VOCAB_IDS[3], SCENE_IDS[3], "모험", "위험을 무릅쓰고 어떤 일에 도전함", "새로운 도전이나 위험한 상황을 표현할 때", "집 짓기는 아기돼지들의 큰 모험이었어요."),
    ]

    for vocab_id, scene_id, word, definition, usage_context, example in vocabs:
        conn.execute(
            sa.text("""
                INSERT INTO scene_vocabularies (id, scene_id, word, definition, usage_context, example_sentence)
                VALUES (:id, :scene_id, :word, :definition, :usage_context, :example)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": vocab_id,
                "scene_id": scene_id,
                "word": word,
                "definition": definition,
                "usage_context": usage_context,
                "example": example,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    for vid in VOCAB_IDS:
        conn.execute(sa.text("DELETE FROM scene_vocabularies WHERE id = :id"), {"id": vid})
    for sid in SCENE_IDS:
        conn.execute(sa.text("DELETE FROM story_scenes WHERE id = :id"), {"id": sid})
    conn.execute(sa.text("DELETE FROM stories WHERE id = :id"), {"id": STORY_ID})
```

- [ ] **Step 2: 시드 마이그레이션 실행**

```bash
docker compose exec api alembic upgrade head
docker compose exec api alembic current
```

Expected: `009 (head)`

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/009_seed_mock_story_three_little_pigs.py
git commit -m "feat: seed mock story data for 아기돼지 삼형제"
```

---

### Task 3: post_activity 스키마 + 도메인 초기화

**Files:**
- Create: `app/domain/post_activity/__init__.py`
- Create: `app/domain/post_activity/schema.py`
- Create: `tests/domain/post_activity/__init__.py`
- Create: `tests/domain/post_activity/test_schema.py`

**Interfaces:**
- Produces:
  - `SceneCard(scene_id: UUID, title: str, image_url: str | None)`
  - `ActivityResponse(attempt_count: int, is_completed: bool, cards: list[SceneCard])`
  - `SubmitRequest(submitted_order: list[UUID])`
  - `VocabularyItem(word: str, definition: str)`
  - `SubmitResponse(is_correct: bool, attempt_count: int, vocabulary: list[VocabularyItem] | None)`
  - `RetellRequest(retelling_text: str)`
  - `RetellResponse(story_title: str, utterance_count: int, new_vocabulary_count: int)`

- [ ] **Step 1: `__init__.py` 생성**

`app/domain/post_activity/__init__.py` — 빈 파일
`tests/domain/post_activity/__init__.py` — 빈 파일

- [ ] **Step 2: 스키마 작성**

`app/domain/post_activity/schema.py`:

```python
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
```

- [ ] **Step 3: 스키마 유효성 테스트 작성**

`tests/domain/post_activity/test_schema.py`:

```python
import uuid

from app.domain.post_activity.schema import (
    ActivityResponse,
    RetellRequest,
    RetellResponse,
    SceneCard,
    SubmitRequest,
    SubmitResponse,
    VocabularyItem,
)


def test_scene_card_accepts_null_image():
    card = SceneCard(scene_id=uuid.uuid4(), title="가벼운 지푸라기집", image_url=None)
    assert card.image_url is None


def test_activity_response_cards_list():
    card = SceneCard(scene_id=uuid.uuid4(), title="튼튼한 벽돌집", image_url=None)
    resp = ActivityResponse(attempt_count=0, is_completed=False, cards=[card])
    assert len(resp.cards) == 1
    assert resp.attempt_count == 0


def test_submit_request_parses_uuid_list():
    ids = [uuid.uuid4(), uuid.uuid4()]
    req = SubmitRequest(submitted_order=ids)
    assert len(req.submitted_order) == 2


def test_submit_response_no_vocabulary_when_wrong():
    resp = SubmitResponse(is_correct=False, attempt_count=1)
    assert resp.vocabulary is None


def test_submit_response_includes_vocabulary_when_correct():
    vocab = [VocabularyItem(word="용감한", definition="두렵거나 힘들어도 맞서는")]
    resp = SubmitResponse(is_correct=True, attempt_count=1, vocabulary=vocab)
    assert resp.vocabulary is not None
    assert resp.vocabulary[0].word == "용감한"


def test_retell_request_text():
    req = RetellRequest(retelling_text="옛날에 아기돼지가...")
    assert req.retelling_text == "옛날에 아기돼지가..."


def test_retell_response_fields():
    resp = RetellResponse(story_title="아기돼지 삼형제", utterance_count=8, new_vocabulary_count=4)
    assert resp.utterance_count == 8
    assert resp.new_vocabulary_count == 4
```

- [ ] **Step 4: 테스트 실행**

```bash
uv run pytest tests/domain/post_activity/test_schema.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add app/domain/post_activity/__init__.py app/domain/post_activity/schema.py \
        tests/domain/post_activity/__init__.py tests/domain/post_activity/test_schema.py
git commit -m "feat: add post_activity schema"
```

---

### Task 4: post_activity repository

**Files:**
- Create: `app/domain/post_activity/repository.py`

**Interfaces:**
- Consumes:
  - `StorySession`, `PostActivityResult`, `StoryScene`, `SceneVocabulary`, `Message` from `app.models.*`
- Produces:
  - `PostActivityRepository`
    - `get_session(session_id, parent_id) -> StorySession` — ForbiddenError/NotFoundError
    - `get_or_create_result(session_id) -> PostActivityResult`
    - `get_scenes(story_id) -> list[StoryScene]` — scene_order 오름차순
    - `get_vocabulary(story_id) -> list[SceneVocabulary]`
    - `save_submit(result, is_correct, attempt_count) -> PostActivityResult`
    - `save_retell(result, retelling_text) -> PostActivityResult`
    - `count_child_utterances(session_id) -> int`
    - `count_story_vocabulary(story_id) -> int`

- [ ] **Step 1: repository 작성**

`app/domain/post_activity/repository.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.message import Message
from app.models.post_activity import PostActivityResult
from app.models.story import StoryScene
from app.models.story_session import StorySession
from app.models.vocabulary import SceneVocabulary


class PostActivityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_session(
        self, session_id: uuid.UUID, parent_id: uuid.UUID
    ) -> StorySession:
        result = await self.db.execute(
            select(StorySession)
            .options(selectinload(StorySession.child))
            .where(StorySession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise NotFoundError("세션을 찾을 수 없습니다.")
        if session.child.parent_id != parent_id:
            raise ForbiddenError("접근 권한이 없습니다.")
        return session

    async def get_or_create_result(
        self, session_id: uuid.UUID
    ) -> PostActivityResult:
        result = await self.db.execute(
            select(PostActivityResult).where(
                PostActivityResult.session_id == session_id
            )
        )
        activity = result.scalar_one_or_none()
        if activity is None:
            activity = PostActivityResult(session_id=session_id)
            self.db.add(activity)
            await self.db.commit()
            await self.db.refresh(activity)
        return activity

    async def get_scenes(self, story_id: uuid.UUID) -> list[StoryScene]:
        result = await self.db.execute(
            select(StoryScene)
            .where(StoryScene.story_id == story_id)
            .order_by(StoryScene.scene_order)
        )
        return list(result.scalars().all())

    async def get_vocabulary(self, story_id: uuid.UUID) -> list[SceneVocabulary]:
        result = await self.db.execute(
            select(SceneVocabulary)
            .join(StoryScene)
            .where(StoryScene.story_id == story_id)
        )
        return list(result.scalars().all())

    async def save_submit(
        self,
        activity: PostActivityResult,
        submitted_order: list[str],
        is_correct: bool,
        attempt_count: int,
    ) -> PostActivityResult:
        activity.submitted_order = submitted_order
        activity.is_order_correct = is_correct
        activity.attempt_count = attempt_count
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    async def save_retell(
        self,
        activity: PostActivityResult,
        retelling_text: str,
    ) -> PostActivityResult:
        activity.retelling_text = retelling_text
        activity.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    async def count_child_utterances(self, session_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Message.id)).where(
                Message.session_id == session_id,
                Message.speaker_type == "child",
            )
        )
        return result.scalar_one()

    async def count_story_vocabulary(self, story_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(SceneVocabulary.id))
            .join(StoryScene)
            .where(StoryScene.story_id == story_id)
        )
        return result.scalar_one()
```

- [ ] **Step 2: Commit**

```bash
git add app/domain/post_activity/repository.py
git commit -m "feat: add post_activity repository"
```

---

### Task 5: post_activity service + 테스트

**Files:**
- Create: `app/domain/post_activity/service.py`
- Create: `tests/domain/post_activity/test_service.py`

**Interfaces:**
- Consumes:
  - `PostActivityRepository` (Task 4)
  - `StorySession.status`, `StorySession.story_id`, `StoryScene.id`, `StoryScene.scene_title`, `StoryScene.image_url`
  - `PostActivityResult.is_order_correct`, `PostActivityResult.attempt_count`
  - `SceneVocabulary.word`, `SceneVocabulary.definition`
- Produces:
  - `PostActivityService`
    - `get_activity(session_id, parent_id) -> ActivityResponse`
    - `submit_order(session_id, parent_id, submitted_order) -> SubmitResponse`
    - `save_retell(session_id, parent_id, retelling_text) -> RetellResponse`

- [ ] **Step 1: 실패하는 테스트 먼저 작성**

`tests/domain/post_activity/test_service.py`:

```python
import uuid
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
    from datetime import datetime, timezone
    result = _make_result(attempt_count=1, is_correct=True)
    result.retelling_text = "이야기..."
    result.completed_at = datetime.now(timezone.utc)
    repo.get_session.return_value = session
    repo.get_or_create_result.return_value = result
    repo.get_scenes.return_value = scenes

    resp = await service.get_activity(session.id, session.child.parent_id)

    assert resp.is_completed is True


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
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
uv run pytest tests/domain/post_activity/test_service.py -v
```

Expected: ImportError (service 미구현)

- [ ] **Step 3: service 구현**

`app/domain/post_activity/service.py`:

```python
import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError
from app.domain.post_activity.repository import PostActivityRepository
from app.domain.post_activity.schema import (
    ActivityResponse,
    RetellResponse,
    SceneCard,
    SubmitResponse,
    VocabularyItem,
)


class PostActivityService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = PostActivityRepository(db)

    async def get_activity(
        self, session_id: uuid.UUID, parent_id: uuid.UUID
    ) -> ActivityResponse:
        session = await self.repo.get_session(session_id, parent_id)
        if session.status != "completed":
            raise BadRequestError("세션이 아직 완료되지 않았습니다.")

        activity = await self.repo.get_or_create_result(session_id)
        scenes = await self.repo.get_scenes(session.story_id)

        cards = [
            SceneCard(scene_id=s.id, title=s.scene_title, image_url=s.image_url)
            for s in scenes
        ]
        random.shuffle(cards)

        is_completed = (
            activity.is_order_correct is True and activity.completed_at is not None
        )

        return ActivityResponse(
            attempt_count=activity.attempt_count,
            is_completed=is_completed,
            cards=cards,
        )

    async def submit_order(
        self,
        session_id: uuid.UUID,
        parent_id: uuid.UUID,
        submitted_order: list[uuid.UUID],
    ) -> SubmitResponse:
        session = await self.repo.get_session(session_id, parent_id)
        activity = await self.repo.get_or_create_result(session_id)

        if activity.is_order_correct is True:
            raise BadRequestError("이미 정답 처리된 활동입니다.")

        scenes = await self.repo.get_scenes(session.story_id)

        if len(submitted_order) != len(scenes):
            raise BadRequestError("제출한 씬 수가 올바르지 않습니다.")

        correct_order = [s.id for s in scenes]
        is_correct = submitted_order == correct_order
        new_count = activity.attempt_count + 1

        updated = await self.repo.save_submit(
            activity,
            [str(sid) for sid in submitted_order],
            is_correct,
            new_count,
        )

        if not is_correct:
            return SubmitResponse(is_correct=False, attempt_count=updated.attempt_count)

        vocab_rows = await self.repo.get_vocabulary(session.story_id)
        vocabulary = [
            VocabularyItem(word=v.word, definition=v.definition) for v in vocab_rows
        ]
        return SubmitResponse(
            is_correct=True,
            attempt_count=updated.attempt_count,
            vocabulary=vocabulary,
        )

    async def save_retell(
        self,
        session_id: uuid.UUID,
        parent_id: uuid.UUID,
        retelling_text: str,
    ) -> RetellResponse:
        session = await self.repo.get_session(session_id, parent_id)
        activity = await self.repo.get_or_create_result(session_id)

        if not activity.is_order_correct:
            raise BadRequestError("순서 맞추기를 먼저 완료해야 합니다.")

        await self.repo.save_retell(activity, retelling_text)

        utterance_count = await self.repo.count_child_utterances(session_id)
        new_vocabulary_count = await self.repo.count_story_vocabulary(session.story_id)

        return RetellResponse(
            story_title=session.story.title,
            utterance_count=utterance_count,
            new_vocabulary_count=new_vocabulary_count,
        )
```

- [ ] **Step 4: 테스트 실행 (통과 확인)**

```bash
uv run pytest tests/domain/post_activity/test_service.py -v
```

Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add app/domain/post_activity/service.py tests/domain/post_activity/test_service.py
git commit -m "feat: add post_activity service"
```

---

### Task 6: post_activity router + main.py 등록

**Files:**
- Create: `app/domain/post_activity/router.py`
- Modify: `main.py`

**Interfaces:**
- Consumes:
  - `PostActivityService` (Task 5)
  - `CurrentUser`, `DBSession` from `app.core.dependencies`
  - `SubmitRequest`, `RetellRequest` (Task 3)

- [ ] **Step 1: router 작성**

`app/domain/post_activity/router.py`:

```python
import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentUser, DBSession
from app.domain.post_activity.schema import (
    ActivityResponse,
    RetellRequest,
    RetellResponse,
    SubmitRequest,
    SubmitResponse,
)
from app.domain.post_activity.service import PostActivityService

router = APIRouter(prefix="/sessions", tags=["post-activity"])


def _get_service(db: DBSession) -> PostActivityService:
    return PostActivityService(db)


@router.get("/{session_id}/post-activity", response_model=ActivityResponse)
async def get_activity(
    session_id: uuid.UUID,
    user: CurrentUser,
    service: PostActivityService = Depends(_get_service),
):
    return await service.get_activity(session_id, user.id)


@router.post("/{session_id}/post-activity/submit", response_model=SubmitResponse)
async def submit_order(
    session_id: uuid.UUID,
    body: SubmitRequest,
    user: CurrentUser,
    service: PostActivityService = Depends(_get_service),
):
    return await service.submit_order(session_id, user.id, body.submitted_order)


@router.post("/{session_id}/post-activity/retell", response_model=RetellResponse)
async def save_retell(
    session_id: uuid.UUID,
    body: RetellRequest,
    user: CurrentUser,
    service: PostActivityService = Depends(_get_service),
):
    return await service.save_retell(session_id, user.id, body.retelling_text)
```

- [ ] **Step 2: main.py에 라우터 등록**

`main.py`에 아래 두 줄 추가:

import 블록에:
```python
from app.domain.post_activity.router import router as post_activity_router
```

라우터 등록 블록에:
```python
app.include_router(post_activity_router)
```

- [ ] **Step 3: 서버 기동 확인**

```bash
uv run fastapi dev main.py
```

브라우저에서 `http://localhost:8000/docs` 열어 `/sessions/{session_id}/post-activity` 엔드포인트 3개가 보이는지 확인.

- [ ] **Step 4: 전체 테스트 실행**

```bash
uv run pytest tests/domain/post_activity/ -v
```

Expected: 모두 passed

- [ ] **Step 5: Commit**

```bash
git add app/domain/post_activity/router.py main.py
git commit -m "feat: register post_activity router"
```

---

## 완료 기준

- [ ] `alembic upgrade head` 성공 (009까지)
- [ ] DB에 아기돼지 삼형제 스토리 5개 씬, 4개 단어 확인
- [ ] `GET /sessions/{id}/post-activity` → 셔플된 카드 5개 반환
- [ ] `POST /sessions/{id}/post-activity/submit` → 오답 시 vocabulary 없음, 정답 시 vocabulary 4개
- [ ] `POST /sessions/{id}/post-activity/retell` → story_title, utterance_count, new_vocabulary_count 반환
- [ ] `uv run pytest tests/domain/post_activity/ -v` 전체 통과
