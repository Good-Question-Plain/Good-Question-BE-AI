"""progress scene schema: scene types, missions, nullable dialogue fields

Revision ID: 008
Revises: 007
Create Date: 2026-08-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("stories", sa.Column("content_key", sa.String(), nullable=True))
    op.create_unique_constraint("uq_stories_content_key", "stories", ["content_key"])

    op.add_column(
        "story_scenes",
        sa.Column(
            "scene_type",
            sa.String(),
            nullable=False,
            server_default="narration",
        ),
    )
    op.add_column("story_scenes", sa.Column("content_key", sa.String(), nullable=True))
    op.add_column("story_scenes", sa.Column("character_key", sa.String(), nullable=True))
    op.add_column("story_scenes", sa.Column("mission_condition", sa.Text(), nullable=True))
    op.add_column(
        "story_scenes",
        sa.Column("mission_examples", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.create_unique_constraint(
        "uq_story_scenes_content_key", "story_scenes", ["content_key"]
    )

    op.alter_column(
        "story_scenes", "scene_description", existing_type=sa.Text(), nullable=True
    )
    op.alter_column(
        "story_scenes", "character_name", existing_type=sa.String(), nullable=True
    )
    op.alter_column(
        "story_scenes", "character_opening", existing_type=sa.Text(), nullable=True
    )
    op.alter_column(
        "story_scenes", "character_closing", existing_type=sa.Text(), nullable=True
    )
    op.alter_column(
        "story_scenes", "scene_goal", existing_type=sa.Text(), nullable=True
    )
    op.alter_column(
        "story_scenes", "conflict", existing_type=sa.Text(), nullable=True
    )

    op.alter_column(
        "story_scenes",
        "required_elements",
        existing_type=postgresql.ARRAY(sa.String()),
        nullable=True,
    )
    op.alter_column(
        "story_scenes",
        "max_turns",
        existing_type=sa.SmallInteger(),
        nullable=True,
    )
    op.alter_column(
        "story_scenes",
        "preferred_turns",
        existing_type=sa.SmallInteger(),
        nullable=True,
    )

    op.alter_column(
        "utterance_analyses",
        "child_intent",
        existing_type=sa.String(),
        nullable=True,
    )
    op.alter_column(
        "utterance_analyses",
        "detected_elements",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "utterance_analyses",
        "detected_elements",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
    )
    op.alter_column(
        "utterance_analyses",
        "child_intent",
        existing_type=sa.String(),
        nullable=False,
    )

    op.alter_column(
        "story_scenes",
        "preferred_turns",
        existing_type=sa.SmallInteger(),
        nullable=False,
    )
    op.alter_column(
        "story_scenes",
        "max_turns",
        existing_type=sa.SmallInteger(),
        nullable=False,
    )
    op.alter_column(
        "story_scenes",
        "required_elements",
        existing_type=postgresql.ARRAY(sa.String()),
        nullable=False,
    )
    op.alter_column(
        "story_scenes", "conflict", existing_type=sa.Text(), nullable=False
    )
    op.alter_column(
        "story_scenes", "scene_goal", existing_type=sa.Text(), nullable=False
    )
    op.alter_column(
        "story_scenes", "character_closing", existing_type=sa.Text(), nullable=False
    )
    op.alter_column(
        "story_scenes", "character_opening", existing_type=sa.Text(), nullable=False
    )
    op.alter_column(
        "story_scenes", "character_name", existing_type=sa.String(), nullable=False
    )
    op.alter_column(
        "story_scenes", "scene_description", existing_type=sa.Text(), nullable=False
    )

    op.drop_constraint("uq_story_scenes_content_key", "story_scenes", type_="unique")
    op.drop_column("story_scenes", "mission_examples")
    op.drop_column("story_scenes", "mission_condition")
    op.drop_column("story_scenes", "character_key")
    op.drop_column("story_scenes", "content_key")
    op.drop_column("story_scenes", "scene_type")

    op.drop_constraint("uq_stories_content_key", "stories", type_="unique")
    op.drop_column("stories", "content_key")
