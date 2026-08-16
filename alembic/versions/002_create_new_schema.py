"""create new schema tables

Revision ID: 002
Revises: 001
Create Date: 2026-08-11
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "children",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("parent_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("birth_year", sa.SmallInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["parents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "child_consents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=False),
        sa.Column("consent_version", sa.String(), nullable=False),
        sa.Column("verification_method", sa.String(), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "stories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("difficulty", sa.String(), nullable=False),
        sa.Column("topics", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("estimated_minutes", sa.SmallInteger(), nullable=True),
        sa.Column(
            "post_activity_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "story_scenes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("story_id", sa.UUID(), nullable=False),
        sa.Column("scene_order", sa.SmallInteger(), nullable=False),
        sa.Column("scene_description", sa.Text(), nullable=False),
        sa.Column("conflict", sa.Text(), nullable=False),
        sa.Column("character_name", sa.String(), nullable=False),
        sa.Column("character_opening", sa.Text(), nullable=False),
        sa.Column("character_closing", sa.Text(), nullable=False),
        sa.Column("scene_goal", sa.Text(), nullable=False),
        sa.Column("required_elements", sa.ARRAY(sa.String()), nullable=False),
        sa.Column("preferred_turns", sa.SmallInteger(), nullable=False),
        sa.Column("max_turns", sa.SmallInteger(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id", "scene_order", name="uq_story_scene_order"),
    )

    op.create_table(
        "story_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=False),
        sa.Column("story_id", sa.UUID(), nullable=False),
        sa.Column("current_scene_id", sa.UUID(), nullable=True),
        sa.Column(
            "current_child_turn_count",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "accumulated_elements",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "last_detected_elements",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("last_response_mode", sa.String(), nullable=True),
        sa.Column("last_guidance_target", sa.String(), nullable=True),
        sa.Column(
            "turns_without_new_element",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "consecutive_low_information_turns",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "scene_goal_met",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("scene_end_reason", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default=sa.text("'in_progress'"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_activity_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_scene_id"], ["story_scenes.id"]),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("scene_id", sa.UUID(), nullable=False),
        sa.Column("speaker_type", sa.String(), nullable=False),
        sa.Column("turn_order", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("stt_raw_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scene_id"], ["story_scenes.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["story_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "utterance_analyses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column("child_intent", sa.String(), nullable=False),
        sa.Column("main_point", sa.Text(), nullable=True),
        sa.Column(
            "detected_elements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("utterance_validity", sa.String(), nullable=False),
        sa.Column(
            "analysis_version",
            sa.String(),
            nullable=False,
            server_default=sa.text("'mvp_v1'"),
        ),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", name="uq_utterance_analysis_message"),
    )

    op.create_table(
        "post_activity_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("submitted_order", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("is_order_correct", sa.Boolean(), nullable=True),
        sa.Column(
            "attempt_count",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("retelling_text", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["story_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_post_activity_session"),
    )


def downgrade() -> None:
    op.drop_table("post_activity_results")
    op.drop_table("utterance_analyses")
    op.drop_table("messages")
    op.drop_table("story_sessions")
    op.drop_table("story_scenes")
    op.drop_table("stories")
    op.drop_table("child_consents")
    op.drop_table("children")
    op.drop_table("parents")
