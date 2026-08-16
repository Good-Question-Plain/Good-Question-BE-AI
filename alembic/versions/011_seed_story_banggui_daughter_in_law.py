"""seed story: 방귀 뀌는 며느리

Revision ID: 011
Revises: 010
Create Date: 2026-08-15
"""

import sqlalchemy as sa
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

STORY_ID = "22222222-2222-2222-2222-222222222222"

# sc_banggui_01 ~ sc_banggui_09 (도입1, 전개1, 대화1, 전개2, 대화2, 전개3, 대화3, 전개4, 대화4)
SCENE_IDS = [
    "32222222-2222-2222-2222-222222222201",
    "32222222-2222-2222-2222-222222222202",
    "32222222-2222-2222-2222-222222222203",
    "32222222-2222-2222-2222-222222222204",
    "32222222-2222-2222-2222-222222222205",
    "32222222-2222-2222-2222-222222222206",
    "32222222-2222-2222-2222-222222222207",
    "32222222-2222-2222-2222-222222222208",
    "32222222-2222-2222-2222-222222222209",
]


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text("""
            INSERT INTO stories (id, title, summary, difficulty, topics, estimated_minutes, status)
            VALUES (
                :id, :title, :summary, :difficulty,
                ARRAY['다름','자기이해','장점 발견'],
                :estimated_minutes, :status
            )
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id": STORY_ID,
            "title": "방귀 뀌는 며느리",
            "summary": "큰 방귀를 부끄러워하던 며느리가 자신의 다름을 장점으로 바꾸는 이야기",
            "difficulty": "보통",
            "estimated_minutes": 20,
            "status": "published",
        },
    )

    # 서사 장면 (도입·전개): 캐릭터 대화 없음
    narrative_scenes = [
        (
            SCENE_IDS[0], 1, "방귀 뀌는 며느리",  # scene_title: mock
            "옛날 어느 마을에 방귀를 아주 크게 뀌는 며느리가 살았습니다. 며느리는 시집에 온 뒤로 늘 얌전하고 예의 바르게 보이고 싶었습니다. 시댁 식구들이 자신을 이상하게 볼까 봐 걱정했기 때문입니다.",
        ),
        (
            SCENE_IDS[1], 2, "꾹꾹 참는 며느리",  # scene_title: mock
            "그래서 며느리는 방귀가 나오려고 할 때마다 꾹꾹 참았습니다. 하루도 참고, 이틀도 참고, 그렇게 오래 참다 보니 배는 점점 빵빵하게 부풀어 올랐고 얼굴은 노랗게 변했습니다. 몸도 마음도 너무 힘들었지만, 며느리는 차마 가족들에게 솔직하게 말하지 못했습니다.",
        ),
        (
            SCENE_IDS[3], 4, "터져버린 방귀",  # scene_title: mock
            "며느리는 더 이상 참을 수 없어 몰래 살짝만 방귀를 뀌려고 합니다. 하지만 오래 참았던 탓에 방귀가 크게 터져 나왔습니다. 마당의 먼지가 휘리릭 날아가고, 기왓장이 달그락거리고, 시아버지의 갓까지 휙 날아가 버렸습니다.",
        ),
        (
            SCENE_IDS[5], 6, "높은 배나무",  # scene_title: mock
            "한참 걷다 보니 아랫마을 길가에 아주 높은 배나무가 한 그루 서 있었습니다. 나무 꼭대기에는 노랗고 탐스러운 배들이 주렁주렁 매달려 있었습니다. 시아버지는 배를 보자 군침이 돌았습니다. 마침 아랫마을 사람들도 그 배를 먹고 싶어 했지만, 나무가 너무 높아 아무도 딸 수 없었습니다.",
        ),
        (
            SCENE_IDS[7], 8, "시아버지의 후회",  # scene_title: mock
            "시아버지는 며느리의 방귀가 시끄럽고 별난 것이 아니라, 모두를 도울 수 있는 특별한 힘이라는 것을 깨닫습니다. 자신이 며느리를 구박했던 일을 후회하고 사과합니다.",
        ),
    ]

    for scene_id, order, title, description in narrative_scenes:
        conn.execute(
            sa.text("""
                INSERT INTO story_scenes (
                    id, story_id, scene_order, scene_title, scene_description,
                    conflict, character_name, character_opening, character_closing,
                    scene_goal, required_elements, preferred_turns, max_turns
                )
                VALUES (
                    :id, :story_id, :order, :title, :description,
                    '', '', '', '',
                    '', ARRAY[]::text[], 0, 0
                )
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": scene_id,
                "story_id": STORY_ID,
                "order": order,
                "title": title,
                "description": description,
            },
        )

    # 대화 장면 1 — sc_banggui_03 (방귀쟁이 며느리)
    conn.execute(
        sa.text("""
            INSERT INTO story_scenes (
                id, story_id, scene_order, scene_title, scene_description,
                conflict, character_name, character_opening, character_closing,
                scene_goal, required_elements, preferred_turns, max_turns
            )
            VALUES (
                :id, :story_id, 3, :title, '',
                :conflict, :char_name, :opening, :closing,
                :goal, ARRAY['PERSPECTIVE','EMOTION','REASON','SOLUTION'], 3, 4
            )
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id": SCENE_IDS[2],
            "story_id": STORY_ID,
            "title": "며느리의 고민",  # scene_title: mock
            "conflict": "방귀를 숨기고 싶어하는 며느리의 고민",
            "char_name": "방귀쟁이 며느리",
            "opening": "ㅇㅇ아, 내 방귀가 너무 크다는 걸 알면 가족들이 나를 이상하게 생각하지 않을까?",
            "closing": "그래도 아직은 못 말하겠어. 조금만 더 참아 볼게.",
            "goal": "방귀를 숨기고 싶어하는 며느리의 입장을 이해하고, 공감해주며 문제를 숨기지 않고 솔직하게 말할 수 있는 용기를 준다",
        },
    )

    # 대화 장면 2 — sc_banggui_05 (시아버지)
    conn.execute(
        sa.text("""
            INSERT INTO story_scenes (
                id, story_id, scene_order, scene_title, scene_description,
                conflict, character_name, character_opening, character_closing,
                scene_goal, required_elements, preferred_turns, max_turns
            )
            VALUES (
                :id, :story_id, 5, :title, '',
                :conflict, :char_name, :opening, :closing,
                :goal, ARRAY['PERSPECTIVE','EMOTION','REASON','SOLUTION'], 4, 5
            )
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id": SCENE_IDS[4],
            "story_id": STORY_ID,
            "title": "화난 시아버지",  # scene_title: mock
            "conflict": "화난 시아버지가 며느리를 쫓아내려 하는 상황",
            "char_name": "시아버지",
            "opening": "아이고 이게 무슨 일이냐! 우리 집안이 다 흔들리는구나! 이렇게 창피한 며느리와 함께 못살겠다! 그렇지 않니?",
            "closing": "흥, 그래도 도저히 이런 며느리와는 함께 살 수 없으니 친정으로 데려다줘야겠다.",
            "goal": "시아버지가 놀란 마음을 이해하면서도, 며느리가 일부러 그런 것이 아니라 오래 참아서 힘들었던 것임을 말하고, 며느리를 따뜻하게 이해해 달라고 설득한다.",
        },
    )

    # 대화 장면 3 — sc_banggui_07 (마을 이장)
    conn.execute(
        sa.text("""
            INSERT INTO story_scenes (
                id, story_id, scene_order, scene_title, scene_description,
                conflict, character_name, character_opening, character_closing,
                scene_goal, required_elements, preferred_turns, max_turns
            )
            VALUES (
                :id, :story_id, 7, :title, '',
                :conflict, :char_name, :opening, :closing,
                :goal, ARRAY['SOLUTION','REASON','REQUEST','RESULT'], 4, 5
            )
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id": SCENE_IDS[6],
            "story_id": STORY_ID,
            "title": "배를 따는 방법",  # scene_title: mock
            "conflict": "높은 배나무에서 배를 따야 하는 문제 상황",
            "char_name": "마을 이장",
            "opening": "이 배나무는 해마다 탐스러운 배가 열리지만, 너무 높아서 아무도 딸 수가 없었소. 무슨 뾰족한 방법이 없겠는가?",
            "closing": "아이고, 방귀 뀌는 며느리 덕분에 온 마을이 배 잔치를 할 수 있겠구려, 고맙소!",
            "goal": "높은 배나무의 배를 떨어뜨릴 방법을 생각하고, 며느리의 큰 방귀를 안전하게 사용할 수 있는 해결책을 제안한다.",
        },
    )

    # 대화 장면 4 — sc_banggui_09 (방귀쟁이 며느리)
    conn.execute(
        sa.text("""
            INSERT INTO story_scenes (
                id, story_id, scene_order, scene_title, scene_description,
                conflict, character_name, character_opening, character_closing,
                scene_goal, required_elements, preferred_turns, max_turns
            )
            VALUES (
                :id, :story_id, 9, :title, '',
                :conflict, :char_name, :opening, :closing,
                :goal, ARRAY['EMOTION','PERSPECTIVE','RESULT','SOLUTION'], 3, 4
            )
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "id": SCENE_IDS[8],
            "story_id": STORY_ID,
            "title": "나만의 특별한 힘",  # scene_title: mock
            "conflict": "자신의 방귀를 부끄러워하는 며느리가 자신의 특징을 받아들이도록 돕는 상황",
            "char_name": "방귀쟁이 며느리",
            "opening": "ㅇㅇ이 덕분에 내 방귀가 누군가에게 도움이 될 수 있다는 걸 처음 알았어. 이제는 방귀 소리가 큰 걸 부끄러워하지 않아도 될까?",
            "closing": "이제는 부끄러워하며 숨기지 않고, 조심해서 좋은 일에 써 볼게.",
            "goal": "다름을 인정하고, 자신의 특징을 긍정적으로 받아들이는 태도를 말한다.",
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    for scene_id in SCENE_IDS:
        conn.execute(sa.text("DELETE FROM story_scenes WHERE id = :id"), {"id": scene_id})
    conn.execute(sa.text("DELETE FROM stories WHERE id = :id"), {"id": STORY_ID})
