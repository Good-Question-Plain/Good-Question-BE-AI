"""move character slugs to character_key, keep korean name in character_name

Revision ID: 012
Revises: 011
Create Date: 2026-08-15
"""

import re

import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None

_SLUG = re.compile(r"^(ch|s|sc)_[a-z0-9_]+$", re.IGNORECASE)

KNOWN_CHARACTER_NAMES = {
    "ch_banggui_daughter_in_law": "며느리",
    "ch_banggui_father_in_law": "시아버지",
    "ch_banggui_village_chief": "마을 이장",
}


def _is_slug(value: str | None) -> bool:
    return bool(value and _SLUG.match(value.strip()))


def upgrade() -> None:
    scenes = sa.table(
        "story_scenes",
        sa.column("id", sa.UUID()),
        sa.column("character_name", sa.String()),
        sa.column("character_key", sa.String()),
    )
    conn = op.get_bind()
    rows = conn.execute(
        sa.select(scenes.c.id, scenes.c.character_name, scenes.c.character_key)
    ).fetchall()

    for row in rows:
        name = row.character_name
        key = row.character_key
        new_key = key
        new_name = name

        if _is_slug(name):
            new_key = key or name
            new_name = KNOWN_CHARACTER_NAMES.get(name)
        elif not name and key:
            new_name = KNOWN_CHARACTER_NAMES.get(key)

        if (new_key, new_name) != (key, name):
            conn.execute(
                scenes.update()
                .where(scenes.c.id == row.id)
                .values(character_key=new_key, character_name=new_name)
            )


def downgrade() -> None:
    scenes = sa.table(
        "story_scenes",
        sa.column("id", sa.UUID()),
        sa.column("character_name", sa.String()),
        sa.column("character_key", sa.String()),
    )
    conn = op.get_bind()
    rows = conn.execute(
        sa.select(scenes.c.id, scenes.c.character_name, scenes.c.character_key)
    ).fetchall()
    for row in rows:
        if row.character_key and not row.character_name:
            conn.execute(
                scenes.update()
                .where(scenes.c.id == row.id)
                .values(character_name=row.character_key)
            )
