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
