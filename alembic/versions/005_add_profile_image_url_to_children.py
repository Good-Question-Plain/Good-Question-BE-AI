"""add profile_image_url to children

Revision ID: 005
Revises: 004
Create Date: 2026-08-13
"""

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "children",
        sa.Column("profile_image_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("children", "profile_image_url")
