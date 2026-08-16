"""add profile_image_url to parents

Revision ID: 007
Revises: 006
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parents",
        sa.Column("profile_image_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("parents", "profile_image_url")
