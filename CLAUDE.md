# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 세션 시작 규칙

새 세션(컨텍스트가 비어있거나 아직 문서를 읽지 않은 상태)에서는 아래 순서로 초기 1회 읽기:

1. `docs/PRD.md` — 없으면 건너뜀
2. `docs/TRD.md` — 없으면 건너뜀
3. `docs/WORKFLOW.md` — 없으면 반드시 사용자에게 알림
4. `docs/IMPLEMENTATION_ORDER.md` — 없으면 건너뜀 (구현 순서 및 진행 상황)

로드 완료 후 한 줄 출력: **"PRD / TRD / WORKFLOW / IMPLEMENTATION_ORDER 로드 완료, 작업 준비됐습니다."**

같은 세션 내에서는 재로드하지 않음. 세션 중 문서 내용 참조 시 이미 읽은 내용 사용 (부분 재로드 없음).
재로드는 사용자가 명시적으로 요청하거나, 문서 변경 후 최신 반영을 요청한 경우에만.

.env 파일은 접근 및 조회하지 않는다. (.env.example은 가)

## Git 브랜치 관리

### 브랜치 구조

```
main                 ← 프로덕션
└── develop          ← BE + AI 통합 후 배포 전 검증
    ├── develop-be   ← BE 통합 브랜치
    └── develop-ai   ← AI 통합 브랜치
```

### Feature 브랜치 규칙

- **분기 기준**: `develop-be`에서 분기
- **네이밍**: `feature/{작업명}` (예: `feature/supabase-auth`)
- **PR 없음**: 리뷰어가 본인이므로 PR 없이 직접 머지
- **머지 방식**: `--no-ff` 플래그로 머지 커밋 보존

```bash
# feature 브랜치 시작
git checkout -b feature/{작업명} develop-be

# 작업 완료 후 머지
git checkout develop-be
git merge --no-ff feature/{작업명}
git branch -d feature/{작업명}
```

### 커밋 단위 원칙

- 각 커밋은 독립적으로 빌드 가능한 단위여야 한다
- 함께 바꿔야 앱이 동작하는 파일은 한 커밋으로 묶는다
- 되돌릴 수 없는 작업(DB 테이블 drop 등)은 코드 변경과 분리해 별도 feature 브랜치로 관리한다

### 머지 파이프라인

```
feature/{작업명}  →  develop-be  →  develop  →  main
```

---

## 작업 워크플로우

- **1차 (설계)**: 요구사항 파악 → 해결 방향 탐색 → 구현 방식 설계 → 사용자 승인
- **2차 (구현)**: 승인된 설계 기반 구현 완료
- **3차 (검증)**: 새 세션 서브 에이전트로 구현 결과 검증 → 문제 발견 시 2차 재진입

상세 절차 → [`docs/WORKFLOW.md`](docs/WORKFLOW.md)

## Product & Technical Docs

- [`docs/PRD.md`](docs/PRD.md) — 서비스 개요, 기능 요구사항, AI/백엔드 연동 포인트
- [`docs/TRD.md`](docs/TRD.md) — 기술 스택, 아키텍처, DB 스키마, 인증, 캐싱, 인프라
- [`docs/IMPLEMENTATION_ORDER.md`](docs/IMPLEMENTATION_ORDER.md) — Phase별 구현 순서 및 진행 상황 (작업 완료 시 상태 갱신)

## Commands

```bash
# Install dependencies
uv sync

# Run the application
uv run python main.py

# Run FastAPI dev server (once app is wired up)
uv run fastapi dev main.py

# Add a dependency
uv add <package>
```

## Tech Stack

- **Python 3.14**
- **FastAPI** (with standard extras — includes uvicorn, httpx, etc.)
- **SQLAlchemy 2.x** — use the async ORM style (`async_sessionmaker`, `AsyncSession`)
- **uv** — the sole dependency/venv manager; do not use pip or poetry