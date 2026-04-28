"""Constants for battle simulation."""

# 地形適正による補正係数
TERRAIN_ADAPTABILITY_MODIFIERS = {
    "S": 1.2,
    "A": 1.0,
    "B": 0.8,
    "C": 0.6,
    "D": 0.4,
}

# デフォルトの地形適正（標準的な機体）
DEFAULT_TERRAIN_ADAPTABILITY = {
    "SPACE": "A",
    "GROUND": "A",
    "COLONY": "A",
    "UNDERWATER": "C",
}

# 特殊環境効果の定義
SPECIAL_ENVIRONMENT_EFFECTS: dict[str, dict] = {
    "MINOVSKY": {
        "description": "ミノフスキー粒子: 索敵範囲が半減する",
        "sensor_range_multiplier": 0.5,
    },
    "GRAVITY_WELL": {
        "description": "重力井戸: 機動性が低下する",
        "mobility_multiplier": 0.6,
    },
    "OBSTACLE": {
        "description": "障害物: 命中率が低下する",
        "accuracy_penalty": 10.0,
    },
}

# 武器スロットの最大数
MAX_WEAPON_SLOTS = 2

# 有効な戦略モードのセット
VALID_STRATEGY_MODES: frozenset[str] = frozenset(
    {"AGGRESSIVE", "DEFENSIVE", "SNIPER", "ASSAULT", "RETREAT"}
)

# ユニット種別ごとの慣性パラメータデフォルト値 (Phase 3-1)
INERTIA_DEFAULTS: dict[str, dict[str, float]] = {
    "NORMAL_MS": {
        "max_speed": 80.0,
        "acceleration": 30.0,
        "deceleration": 50.0,
        "max_turn_rate": 360.0,
    },
    "HIGH_MOBILITY_MS": {
        "max_speed": 150.0,
        "acceleration": 60.0,
        "deceleration": 80.0,
        "max_turn_rate": 540.0,
    },
    "MA": {
        "max_speed": 300.0,
        "acceleration": 15.0,
        "deceleration": 8.0,
        "max_turn_rate": 30.0,
    },
    "LARGE_MS": {
        "max_speed": 40.0,
        "acceleration": 10.0,
        "deceleration": 20.0,
        "max_turn_rate": 90.0,
    },
}
