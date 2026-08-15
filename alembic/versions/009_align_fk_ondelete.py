"""align story/session/message FK ondelete policies

Revision ID: 009
Revises: 008
Create Date: 2026-08-14
"""

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("story_sessions_story_id_fkey", "story_sessions", type_="foreignkey")
    op.create_foreign_key(
        "story_sessions_story_id_fkey",
        "story_sessions",
        "stories",
        ["story_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "story_sessions_current_scene_id_fkey", "story_sessions", type_="foreignkey"
    )
    op.create_foreign_key(
        "story_sessions_current_scene_id_fkey",
        "story_sessions",
        "story_scenes",
        ["current_scene_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint("messages_scene_id_fkey", "messages", type_="foreignkey")
    op.create_foreign_key(
        "messages_scene_id_fkey",
        "messages",
        "story_scenes",
        ["scene_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("messages_scene_id_fkey", "messages", type_="foreignkey")
    op.create_foreign_key(
        "messages_scene_id_fkey",
        "messages",
        "story_scenes",
        ["scene_id"],
        ["id"],
    )

    op.drop_constraint(
        "story_sessions_current_scene_id_fkey", "story_sessions", type_="foreignkey"
    )
    op.create_foreign_key(
        "story_sessions_current_scene_id_fkey",
        "story_sessions",
        "story_scenes",
        ["current_scene_id"],
        ["id"],
    )

    op.drop_constraint("story_sessions_story_id_fkey", "story_sessions", type_="foreignkey")
    op.create_foreign_key(
        "story_sessions_story_id_fkey",
        "story_sessions",
        "stories",
        ["story_id"],
        ["id"],
    )
