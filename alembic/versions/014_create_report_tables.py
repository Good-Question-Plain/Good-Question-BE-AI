"""create learning report tables

Revision ID: 014
Revises: 013
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=False),
        sa.Column("story_id", sa.UUID(), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default=sa.text("'generating'"),
        ),
        sa.Column("speech_summary", sa.Text(), nullable=True),
        sa.Column("vocabulary_feedback", sa.Text(), nullable=True),
        sa.Column(
            "expression_patterns",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "expression_items",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "logic_items",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("analyzer_name", sa.String(), nullable=True),
        sa.Column(
            "report_version",
            sa.String(),
            nullable=False,
            server_default=sa.text("'stub_v1'"),
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["story_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_learning_report_session"),
    )
    op.create_index(
        "ix_learning_reports_child_story",
        "learning_reports",
        ["child_id", "story_id"],
    )

    op.create_table(
        "report_vocabularies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=False),
        sa.Column("word", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column("example_sentence", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["report_id"], ["learning_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "word", "kind", name="uq_report_vocabulary_word"),
    )
    op.create_index(
        "ix_report_vocabularies_child_kind",
        "report_vocabularies",
        ["child_id", "kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_report_vocabularies_child_kind", table_name="report_vocabularies")
    op.drop_table("report_vocabularies")
    op.drop_index("ix_learning_reports_child_story", table_name="learning_reports")
    op.drop_table("learning_reports")
