"""scene_vocabularies and child_vocabularies for curious word pick

Revision ID: 006
Revises: 005
Create Date: 2026-08-15
"""

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scene_vocabularies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scene_id", sa.UUID(), nullable=False),
        sa.Column("word", sa.String(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column("example_sentence", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["scene_id"], ["story_scenes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scene_id", "word", name="uq_scene_vocabulary_word"),
    )
    op.create_table(
        "child_vocabularies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("scene_vocabulary_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False, server_default=sa.text("'curious'")),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["story_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["scene_vocabulary_id"], ["scene_vocabularies.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "scene_vocabulary_id",
            name="uq_child_vocabulary_session_word",
        ),
    )
    op.create_index(
        "ix_child_vocabularies_child_id",
        "child_vocabularies",
        ["child_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_child_vocabularies_child_id", table_name="child_vocabularies")
    op.drop_table("child_vocabularies")
    op.drop_table("scene_vocabularies")
