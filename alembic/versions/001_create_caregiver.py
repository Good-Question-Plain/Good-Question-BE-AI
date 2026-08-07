"""create caregiver table

Revision ID: 001
Revises:
Create Date: 2026-08-07 01:37:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "caregiver",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.Column(
            "social_provider",
            sa.Enum("email", "kakao", "google", "naver", name="socialprovider"),
            nullable=False,
        ),
        sa.Column("social_id", sa.String(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )


def downgrade() -> None:
    op.drop_table("caregiver")
    op.execute("DROP TYPE IF EXISTS socialprovider")
