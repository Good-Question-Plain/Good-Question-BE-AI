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
