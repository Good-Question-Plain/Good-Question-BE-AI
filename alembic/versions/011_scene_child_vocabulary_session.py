"""session-scoped child vocabulary picks for curious words

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


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_scene_vocabulary_word", "scene_vocabularies", ["scene_id", "word"]
    )
    op.add_column(
        "child_vocabularies",
        sa.Column("session_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "child_vocabularies_session_id_fkey",
        "child_vocabularies",
        "story_sessions",
        ["session_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.add_column(
        "child_vocabularies",
        sa.Column(
            "kind",
            sa.String(),
            nullable=False,
            server_default=sa.text("'curious'"),
        ),
    )
    op.drop_constraint(
        "uq_child_scene_vocabulary", "child_vocabularies", type_="unique"
    )
    op.create_unique_constraint(
        "uq_child_vocabulary_session_word",
        "child_vocabularies",
        ["session_id", "scene_vocabulary_id"],
    )
    op.create_index(
        "ix_child_vocabularies_child_id",
        "child_vocabularies",
        ["child_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_child_vocabularies_child_id", table_name="child_vocabularies")
    op.drop_constraint(
        "uq_child_vocabulary_session_word", "child_vocabularies", type_="unique"
    )
    op.create_unique_constraint(
        "uq_child_scene_vocabulary",
        "child_vocabularies",
        ["child_id", "scene_vocabulary_id"],
    )
    op.drop_column("child_vocabularies", "kind")
    op.drop_constraint(
        "child_vocabularies_session_id_fkey", "child_vocabularies", type_="foreignkey"
    )
    op.drop_column("child_vocabularies", "session_id")
    op.drop_constraint(
        "uq_scene_vocabulary_word", "scene_vocabularies", type_="unique"
    )
