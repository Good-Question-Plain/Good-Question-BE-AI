"""fix scene image URLs: Korean key → ASCII key

Revision ID: 018
Revises: 017
Create Date: 2026-08-17
"""

import sqlalchemy as sa
from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None

BASE_URL = "https://goodquestion-s3-bucket.s3.ap-northeast-2.amazonaws.com/scenes/banggui"

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

OLD_BASE_URL = "https://goodquestion-s3-bucket.s3.ap-northeast-2.amazonaws.com/scenes/banggui"
OLD_FILENAMES = [
    "1-도입.png", "2-전개1.png", "3-대화1.png", "4-전개2.png",
    "5-대화2.png", "6-전개3.png", "7-대화3-1.png", "10-전개4.png", "11-대화4.png",
]


def upgrade() -> None:
    conn = op.get_bind()
    for (scene_id, filename) in SCENE_IMAGES:
        conn.execute(
            sa.text("UPDATE story_scenes SET image_url = :url WHERE id = :id"),
            {"url": f"{BASE_URL}/{filename}", "id": scene_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for (scene_id, _), old_filename in zip(SCENE_IMAGES, OLD_FILENAMES):
        conn.execute(
            sa.text("UPDATE story_scenes SET image_url = :url WHERE id = :id"),
            {"url": f"{OLD_BASE_URL}/{old_filename}", "id": scene_id},
        )
