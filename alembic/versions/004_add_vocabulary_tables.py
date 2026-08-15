"""add scene_vocabulary and child_vocabulary tables

Revision ID: 004
Revises: 003
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scene_vocabularies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scene_id", sa.UUID(), nullable=False),
        sa.Column("word", sa.String(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("usage_context", sa.Text(), nullable=False),
        sa.Column("example_sentence", sa.Text(), nullable=False),
        sa.Column("audio_url", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["scene_id"], ["story_scenes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "child_vocabularies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=False),
        sa.Column("scene_vocabulary_id", sa.UUID(), nullable=False),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["scene_vocabulary_id"], ["scene_vocabularies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "child_id", "scene_vocabulary_id", name="uq_child_scene_vocabulary"
        ),
    )


def downgrade() -> None:
    op.drop_table("child_vocabularies")
    op.drop_table("scene_vocabularies")
