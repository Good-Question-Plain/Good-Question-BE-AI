import re

from app.models.story import StoryScene

_SLUG = re.compile(r"^(ch|s|sc)_[a-z0-9_]+$", re.IGNORECASE)

KNOWN_CHARACTER_NAMES = {
    "ch_banggui_daughter_in_law": "며느리",
    "ch_banggui_father_in_law": "시아버지",
    "ch_banggui_village_chief": "마을 이장",
}


def is_content_slug(value: str | None) -> bool:
    return bool(value and _SLUG.match(value.strip()))


def display_character_name(
    character_name: str | None,
    character_key: str | None = None,
) -> str | None:
    """AI·화면에 넘길 한글 표시명. 슬러그(ch_/s_/sc_)는 절대 쓰지 않는다."""
    name = (character_name or "").strip() or None
    key = (character_key or "").strip() or None

    if name and not is_content_slug(name):
        return name
    if key and key in KNOWN_CHARACTER_NAMES:
        return KNOWN_CHARACTER_NAMES[key]
    if name and name in KNOWN_CHARACTER_NAMES:
        return KNOWN_CHARACTER_NAMES[name]
    return None


def scene_character_name(scene: StoryScene) -> str | None:
    return display_character_name(scene.character_name, scene.character_key)
