"""add scene images: 방귀 뀌는 며느리

Revision ID: 017
Revises: 016
Create Date: 2026-08-17
"""

import sqlalchemy as sa
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None

BASE_URL = "https://goodquestion-s3-bucket.s3.ap-northeast-2.amazonaws.com/scenes/banggui"

# scene_order → (scene_id, image filename)
SCENE_IMAGES = [
    ("32222222-2222-2222-2222-222222222201", "scene_01.png"),
    ("32222222-2222-2222-2222-222222222202", "scene_02.png"),
    ("32222222-2222-2222-2222-222222222203", "scene_03.png"),
    ("32222222-2222-2222-2222-222222222204", "scene_04.png"),
    ("32222222-2222-2222-2222-222222222205", "scene_05.png"),
    ("32222222-2222-2222-2222-222222222206", "scene_06.png"),
    ("32222222-2222-2222-2222-222222222207", "scene_07.png"),
    ("32222222-2222-2222-2222-222222222208", "scene_08.png"),
    ("32222222-2222-2222-2222-222222222209", "scene_09.png"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for scene_id, filename in SCENE_IMAGES:
        conn.execute(
            sa.text(
                "UPDATE story_scenes SET image_url = :url WHERE id = :id"
            ),
            {"url": f"{BASE_URL}/{filename}", "id": scene_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for scene_id, _ in SCENE_IMAGES:
        conn.execute(
            sa.text(
                "UPDATE story_scenes SET image_url = NULL WHERE id = :id"
            ),
            {"id": scene_id},
        )
