from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — 관계 문자열 해석을 위해 전체 모델 등록
from app.core.config import settings
from app.core.exceptions import AppError, app_error_handler
from app.domain.auth.router import router as auth_router
from app.domain.main.router import router as main_router
from app.domain.story.router import router as story_router
from app.domain.post_activity.router import router as post_activity_router
from app.domain.progress.router import router as progress_router
from app.domain.story.router import router as story_router
from app.domain.user.router import router as user_router
from app.domain.vocabulary.router import reports_router, vocabulary_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Good Question API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)

app.include_router(auth_router)
app.include_router(main_router)
app.include_router(story_router)
