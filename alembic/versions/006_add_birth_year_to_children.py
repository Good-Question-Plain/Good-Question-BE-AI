"""add birth_year to children

Revision ID: 006
Revises: 005
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "children",
        sa.Column("birth_year", sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("children", "birth_year")
