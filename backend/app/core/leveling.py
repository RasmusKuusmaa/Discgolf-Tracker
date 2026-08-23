import math

XP_PER_LEVEL_BASE = 100


def xp_for_level(level: int) -> int:
    if level <= 1:
        return 0
    return XP_PER_LEVEL_BASE * (level - 1) ** 2


def level_for_xp(total_xp: int) -> int:
    if total_xp <= 0:
        return 1
    return 1 + math.isqrt(total_xp // XP_PER_LEVEL_BASE)


def xp_to_next_level(total_xp: int) -> int:
    current_level = level_for_xp(total_xp)
    return xp_for_level(current_level + 1) - total_xp
