import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.domain.progress.ai import ChatHistory
from app.domain.progress.repository import COMPLETED, ProgressRepository
from app.domain.progress.schema import (
    ActiveProgressResponse,
    CompleteResponse,
    ProgressStatusResponse,
    SpeakResponse,
    StartResponse,
    StepResponse,
)
from app.models.child import Child
from app.models.parent import Parent
from app.models.story import Story, StoryScene
from app.models.story_session import StorySession

MAX_INVALID_RETRIES = 3
CONV_TTL_SECONDS = 86400
DEFAULT_MAX_TURNS = 5
NARRATION = "narration"
DIALOGUE = "dialogue"


def _kind(scene: StoryScene) -> str:
    if scene.scene_type == NARRATION:
        return "narration"
    if scene.mission_condition:
        return "mission"
    return "dialogue"


def _fill_name(text: str | None, child_name: str) -> str | None:
    if text is None:
        return None
    return text.replace("{child_name}", child_name).replace("ㅇㅇ", child_name)


def _conv_key(session_id: uuid.UUID, scene_id: uuid.UUID) -> str:
    return f"conv:{session_id}:{scene_id}"


def _chat_history(turns: list[dict]) -> ChatHistory:
    return {
        "turns": [{"speaker": t["speaker"], "text": t["text"]} for t in turns]
    }


class ProgressService:
    def __init__(self, db: AsyncSession, redis: Redis) -> None:
        self.repo = ProgressRepository(db)
        self.redis = redis

    async def start(
        self, parent: Parent, child_id: uuid.UUID, story_id: uuid.UUID
    ) -> StartResponse:
        child = await self._require_child(parent, child_id)
        story = await self._require_story(story_id)
        if not story.scenes:
            raise BadRequestError("스토리에 장면이 없습니다.")

        active = await self.repo.get_in_progress(child_id)
        if active is not None and active.story_id != story_id:
            raise ConflictError("이미 진행 중인 이야기가 있습니다.")

        if active is None:
            first = story.scenes[0]
            session = await self.repo.create_session(child_id, story_id, first.id)
            await self.redis.delete(f"recommended:child:{child_id}")
        else:
            session = active

        step = await self._enter_current(session, child.name, len(story.scenes))
        return StartResponse(
            session_id=session.id,
            story_id=story_id,
            status=session.status,  # type: ignore[arg-type]
            current_step=step.step_index,
            scene_count=step.scene_count,
            step=step,
        )

    async def get_active(
        self, parent: Parent, child_id: uuid.UUID
    ) -> ActiveProgressResponse | None:
        await self._require_child(parent, child_id)
        session = await self.repo.get_in_progress(child_id)
        if session is None or session.current_scene is None:
            return None
        scene_count = await self.repo.count_scenes(session.story_id)
        return ActiveProgressResponse(
            session_id=session.id,
            story_id=session.story_id,
            title=session.story.title,
            thumbnail_url=session.story.thumbnail_url,
            current_step=session.current_scene.scene_order,
            scene_count=scene_count,
        )

    async def get_status(
        self, parent: Parent, child_id: uuid.UUID, story_id: uuid.UUID
    ) -> ProgressStatusResponse:
        await self._require_child(parent, child_id)
        session = await self.repo.get_latest_for_story(child_id, story_id)
        if session is None:
            raise NotFoundError("진행 중인 이야기를 찾을 수 없습니다.")
        scene = session.current_scene
        scene_count = await self.repo.count_scenes(story_id)
        return ProgressStatusResponse(
            session_id=session.id,
            status=session.status,  # type: ignore[arg-type]
            current_step=scene.scene_order if scene else 0,
            scene_count=scene_count,
            current_kind=_kind(scene) if scene else None,  # type: ignore[arg-type]
            turn=session.current_child_turn_count if scene and scene.scene_type == DIALOGUE else None,
            max_turns=scene.max_turns if scene and scene.scene_type == DIALOGUE else None,
        )

    async def enter_step(
        self,
        parent: Parent,
        child_id: uuid.UUID,
        story_id: uuid.UUID,
        step_index: int,
    ) -> StepResponse:
        child = await self._require_child(parent, child_id)
        story = await self._require_story(story_id)
        session = await self._require_in_progress(child_id, story_id)
        if session.current_scene is None:
            raise NotFoundError("현재 장면을 찾을 수 없습니다.")

        current_order = session.current_scene.scene_order
        scene_count = len(story.scenes)

        if step_index == current_order:
            return await self._enter_current(session, child.name, scene_count)

        if step_index == current_order + 1:
            if not session.scene_end_reason:
                raise ConflictError("아직 현재 단계를 끝내지 않았습니다.")
            if await self._has_open_dialogue(session):
                raise ConflictError("아직 현재 단계를 끝내지 않았습니다.")
            next_scene = await self.repo.get_scene(story_id, step_index)
            if next_scene is None:
                raise NotFoundError("스토리 단계를 찾을 수 없습니다.")
            self._reset_scene_state(session, next_scene)
            await self.repo.save(session)
            session = await self.repo.get_latest_for_story(child_id, story_id)
            assert session is not None
            return await self._enter_current(session, child.name, scene_count)

        raise ConflictError("해당 단계로 이동할 수 없습니다.")

    async def speak(
        self,
        parent: Parent,
        child_id: uuid.UUID,
        story_id: uuid.UUID,
        step_index: int,
        audio: bytes,
    ) -> SpeakResponse:
        child = await self._require_child(parent, child_id)
        await self._require_story(story_id)
        session = await self._require_in_progress(child_id, story_id)
        scene = session.current_scene
        if scene is None or scene.scene_order != step_index:
            raise ConflictError("현재 단계와 다른 장면입니다.")
        if scene.scene_type != DIALOGUE:
            raise BadRequestError("이 장면에서는 말할 수 없습니다.")
        if session.scene_end_reason:
            raise ConflictError("이미 끝난 장면입니다.")
        if not audio:
            raise BadRequestError("오디오 파일이 비어 있습니다.")

        await self._load_or_init_conv(session, scene, child.name)
        max_turns = scene.max_turns or DEFAULT_MAX_TURNS

        # AI 이후 개발
        # do_stt(audio, story.summary) → text
        # check_correct_chat(...) → 실패 시 되묻기, 연속 3회면 강제 진행
        # Redis에 child 저장, turn += 1
        # check_mission_condition(...) → 미션 노출
        # max_turns 또는 check_end_condition(...) → closing 저장 후 messages 플러시
        # 아니면 make_chat(...) → 캐릭터 대사
        pass

        return SpeakResponse(
            accepted=True,
            child_text="",
            character_line=None,
            turn=session.current_child_turn_count,
            max_turns=max_turns,
            mission=None,
            scene_ended=False,
            end_reason=None,
        )

    async def complete(
        self,
        parent: Parent,
        child_id: uuid.UUID,
        story_id: uuid.UUID,
        step_index: int,
        background_tasks: BackgroundTasks,
    ) -> CompleteResponse:
        await self._require_child(parent, child_id)
        story = await self._require_story(story_id)
        session = await self._require_in_progress(child_id, story_id)
        scene = session.current_scene
        if scene is None or scene.scene_order != step_index:
            raise ConflictError("현재 단계와 다른 장면입니다.")

        scene_count = len(story.scenes)

        if scene.scene_type == DIALOGUE:
            if not session.scene_end_reason:
                raise ConflictError("대화가 아직 끝나지 않았습니다.")
            return CompleteResponse(
                current_step=step_index,
                scene_count=scene_count,
                status=session.status,  # type: ignore[arg-type]
                completed=session.status == COMPLETED,
            )

        session.scene_goal_met = True
        session.scene_end_reason = "narration_done"
        story_just_completed = scene.scene_order == scene_count
        if story_just_completed:
            session.status = COMPLETED
            session.completed_at = datetime.now(timezone.utc)
        await self.repo.save(session)
        if story_just_completed:
            from app.domain.vocabulary.service import ReportService

            await ReportService(self.repo.db).enqueue_for_completed_session(
                session, background_tasks
            )
        return CompleteResponse(
            current_step=step_index,
            scene_count=scene_count,
            status=session.status,  # type: ignore[arg-type]
            completed=session.status == COMPLETED,
        )

    async def _enter_current(
        self, session: StorySession, child_name: str, scene_count: int
    ) -> StepResponse:
        scene = session.current_scene
        if scene is None:
            raise NotFoundError("현재 장면을 찾을 수 없습니다.")

        if (
            scene.scene_type == DIALOGUE
            and not session.scene_end_reason
            and not await self.repo.scene_has_messages(session.id, scene.id)
        ):
            await self._load_or_init_conv(session, scene, child_name)
            await self.repo.save(session)

        turn = (
            session.current_child_turn_count
            if scene.scene_type == DIALOGUE
            else None
        )
        return StepResponse(
            step_index=scene.scene_order,
            scene_count=scene_count,
            kind=_kind(scene),  # type: ignore[arg-type]
            scene_id=scene.id,
            scene_description=_fill_name(scene.scene_description, child_name),
            image_url=scene.image_url,
            character_name=scene.character_name,
            character_opening=_fill_name(scene.character_opening, child_name),
            character_closing=None,
            max_turns=scene.max_turns if scene.scene_type == DIALOGUE else None,
            turn=turn,
            mission=None,
        )

    async def _load_or_init_conv(
        self, session: StorySession, scene: StoryScene, child_name: str
    ) -> dict[str, Any]:
        raw = await self.redis.get(_conv_key(session.id, scene.id))
        if raw is not None:
            return json.loads(raw)

        opening = _fill_name(scene.character_opening, child_name)
        conv: dict[str, Any] = {
            "turns": (
                [{"speaker": "character", "text": opening}] if opening else []
            ),
            "invalid_streak": 0,
            "mission_shown": False,
        }
        session.current_child_turn_count = 0
        await self._save_conv(session.id, scene.id, conv)
        return conv

    async def _save_conv(
        self, session_id: uuid.UUID, scene_id: uuid.UUID, conv: dict[str, Any]
    ) -> None:
        await self.redis.set(
            _conv_key(session_id, scene_id),
            json.dumps(conv, ensure_ascii=False),
            ex=CONV_TTL_SECONDS,
        )

    async def _flush_conv(
        self, session: StorySession, scene: StoryScene, conv: dict[str, Any]
    ) -> None:
        await self.repo.flush_turns(session.id, scene.id, conv["turns"])
        await self.redis.delete(_conv_key(session.id, scene.id))

    async def _has_open_dialogue(self, session: StorySession) -> bool:
        scene = session.current_scene
        if scene is None or scene.scene_type != DIALOGUE:
            return False
        if session.scene_end_reason:
            return False
        return await self.redis.exists(_conv_key(session.id, scene.id)) == 1

    def _reset_scene_state(self, session: StorySession, scene: StoryScene) -> None:
        session.current_scene_id = scene.id
        session.current_scene = scene
        session.current_child_turn_count = 0
        session.scene_goal_met = False
        session.scene_end_reason = None
        session.accumulated_elements = []
        session.last_detected_elements = []
        session.last_response_mode = None
        session.last_guidance_target = None
        session.turns_without_new_element = 0
        session.consecutive_low_information_turns = 0

    async def _require_child(self, parent: Parent, child_id: uuid.UUID) -> Child:
        child = await self.repo.get_child(child_id, parent.id)
        if child is None:
            raise ForbiddenError("해당 자녀 프로필에 접근할 수 없습니다.")
        return child

    async def _require_story(self, story_id: uuid.UUID) -> Story:
        story = await self.repo.get_published_story(story_id)
        if story is None:
            raise NotFoundError("스토리를 찾을 수 없습니다.")
        return story

    async def _require_in_progress(
        self, child_id: uuid.UUID, story_id: uuid.UUID
    ) -> StorySession:
        session = await self.repo.get_in_progress(child_id)
        if session is None or session.story_id != story_id:
            raise NotFoundError("진행 중인 이야기를 찾을 수 없습니다.")
        return session
