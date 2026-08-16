"""add thumbnail: 방귀 뀌는 며느리

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

STORY_ID = "22222222-2222-2222-2222-222222222222"
THUMBNAIL_KEY = "stories/banggui/thumbnail.png"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE stories SET thumbnail_url = :key WHERE id = :id"),
        {"key": THUMBNAIL_KEY, "id": STORY_ID},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE stories SET thumbnail_url = NULL WHERE id = :id"),
        {"id": STORY_ID},
    )
