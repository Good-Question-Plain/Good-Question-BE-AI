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
