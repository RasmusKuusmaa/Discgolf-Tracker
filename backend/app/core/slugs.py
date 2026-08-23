import re
from difflib import SequenceMatcher


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "course"


def similar_course_names(a: str, b: str) -> bool:
    slug_a, slug_b = slugify(a), slugify(b)
    if slug_a == slug_b or slug_a in slug_b or slug_b in slug_a:
        return True
    return SequenceMatcher(None, slug_a, slug_b).ratio() >= 0.6
