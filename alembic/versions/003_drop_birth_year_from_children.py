"""drop birth_year from children

Revision ID: 003
Revises: 002
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("children", "birth_year")


def downgrade() -> None:
    op.add_column(
        "children",
        sa.Column("birth_year", sa.SmallInteger(), nullable=False, server_default="0"),
    )
