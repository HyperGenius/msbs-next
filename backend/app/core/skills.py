"""パイロットスキルのマスターデータ定義."""

from typing import TypedDict


class SkillDefinition(TypedDict):
    """スキル定義."""

    id: str
    name: str
    description: str
    effect_per_level: float
    max_level: int


# スキルマスターデータ
SKILL_MASTER_DATA: dict[str, SkillDefinition] = {
    "accuracy_up": {
        "id": "accuracy_up",
        "name": "命中率向上",
        "description": "命中率が上昇する",
        "effect_per_level": 2.0,  # +2% / Lv
        "max_level": 10,
    },
    "evasion_up": {
        "id": "evasion_up",
        "name": "回避率向上",
        "description": "敵の攻撃を回避しやすくなる",
        "effect_per_level": 2.0,  # +2% / Lv
        "max_level": 10,
    },
    "damage_up": {
        "id": "damage_up",
        "name": "攻撃力向上",
        "description": "与えるダメージが増加する",
        "effect_per_level": 3.0,  # +3% / Lv
        "max_level": 10,
    },
    "crit_rate_up": {
        "id": "crit_rate_up",
        "name": "クリティカル率向上",
        "description": "クリティカルヒットが発生しやすくなる",
        "effect_per_level": 1.0,  # +1% / Lv
        "max_level": 10,
    },
}

# スキルポイントコスト（一律1 SP）
SKILL_COST = 1


def get_skill_definition(skill_id: str) -> SkillDefinition | None:
    """スキル定義を取得する.

    Args:
        skill_id: スキルID

    Returns:
        SkillDefinition | None: スキル定義。存在しない場合はNone
    """
    return SKILL_MASTER_DATA.get(skill_id)


def get_all_skills() -> list[SkillDefinition]:
    """全スキル定義を取得する.

    Returns:
        list[SkillDefinition]: スキル定義のリスト
    """
    return list(SKILL_MASTER_DATA.values())
