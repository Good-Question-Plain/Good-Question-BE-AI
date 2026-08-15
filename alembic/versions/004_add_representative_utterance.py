"""add representative utterance to learning reports

Revision ID: 004
Revises: 003
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_reports",
        sa.Column("representative_message_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "learning_reports",
        sa.Column("representative_quote", sa.Text(), nullable=True),
    )
    op.add_column(
        "learning_reports",
        sa.Column("representative_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "learning_reports",
        sa.Column(
            "representative_elements",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.create_foreign_key(
        "fk_learning_report_representative_message",
        "learning_reports",
        "messages",
        ["representative_message_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_learning_report_representative_message",
        "learning_reports",
        type_="foreignkey",
    )
    op.drop_column("learning_reports", "representative_elements")
    op.drop_column("learning_reports", "representative_reason")
    op.drop_column("learning_reports", "representative_quote")
    op.drop_column("learning_reports", "representative_message_id")
