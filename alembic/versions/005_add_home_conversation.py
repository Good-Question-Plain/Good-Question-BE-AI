"""add home conversation questions to learning reports

Revision ID: 005
Revises: 004
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in ("story_topic_questions", "daily_life_questions"):
        op.add_column(
            "learning_reports",
            sa.Column(
                column,
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )


def downgrade() -> None:
    op.drop_column("learning_reports", "daily_life_questions")
    op.drop_column("learning_reports", "story_topic_questions")
