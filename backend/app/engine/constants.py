"""Constants for battle simulation."""

from pathlib import Path

# ファジィルール JSON ディレクトリ (Phase 5-2)
FUZZY_RULES_DIR: Path = Path(__file__).parent.parent.parent / "data" / "fuzzy_rules"

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
        "body_turn_rate": 720.0,
    },
    "HIGH_MOBILITY_MS": {
        "max_speed": 150.0,
        "acceleration": 60.0,
        "deceleration": 80.0,
        "max_turn_rate": 540.0,
        "body_turn_rate": 900.0,
    },
    "MA": {
        "max_speed": 300.0,
        "acceleration": 15.0,
        "deceleration": 8.0,
        "max_turn_rate": 30.0,
        "body_turn_rate": 180.0,
    },
    "LARGE_MS": {
        "max_speed": 40.0,
        "acceleration": 10.0,
        "deceleration": 20.0,
        "max_turn_rate": 90.0,
        "body_turn_rate": 90.0,
    },
}

# ポテンシャルフィールド設定 (Phase 3-2)
ALLY_REPULSION_RADIUS: float = 150.0  # 味方斥力が働く半径 (m)
BOUNDARY_MARGIN: float = 200.0  # マップ境界からの斥力発生距離 (m)
HIGH_THREAT_THRESHOLD: float = 0.5  # 高脅威敵の閾値（脅威度スコア）
MAP_BOUNDS: tuple[float, float] = (0.0, 5000.0)  # XZ方向のマップ範囲 (m)

# 撤退ポイント引力係数 (Phase 3-3)
RETREAT_ATTRACTION_COEFF: float = 5.0  # 撤退ポイントへの強引力係数

# 戦略評価インターバル (Phase 4-2)
STRATEGY_UPDATE_INTERVAL: int = 10  # 何ステップごとに戦略評価を行うか

# バランス調整CLIツール 警告しきい値 (Phase 5-3) — チューニング可能
BALANCE_WARN_DRAW_RATE: float = 0.20  # 引き分け率がこれを超えると警告
BALANCE_WARN_WIN_RATE: float = 0.80  # 勝率がこれを超えると警告（一方的優位）
BALANCE_WARN_AVG_DURATION: float = 200.0  # 平均戦闘時間（秒）がこれを超えると警告

# 障害物システム定数 (Phase A — LOS システム)
OBSTACLE_MARGIN: float = 50.0  # 障害物斥力が働く追加マージン (m)
OBSTACLE_REPULSION_COEFF: float = 4.0  # 障害物への斥力係数

# ブーストダッシュシステム定数 (Phase B)
MELEE_RANGE: float = 50.0  # 近接攻撃有効距離 (m)
MELEE_BOOST_ARRIVAL_RANGE: float = (
    100.0  # ブーストキャンセル目安距離 = MELEE_RANGE × 2 (m)
)
DEFAULT_BOOST_SPEED_MULTIPLIER: float = (
    2.0  # ブースト時速度倍率（max_speed × multiplier）
)
DEFAULT_BOOST_EN_COST: float = 5.0  # ブースト中 EN 消費量 (/s)
DEFAULT_BOOST_MAX_DURATION: float = 3.0  # 1 回のブーストの最大継続時間 (s)
DEFAULT_BOOST_COOLDOWN: float = 5.0  # ブースト終了後の再使用不可時間 (s)

# 近接戦闘システム定数 (Phase C)
POST_MELEE_DISTANCE: float = 10.0  # 格闘命中後の再配置距離 (m)
CLOSE_RANGE: float = 200.0  # 近距離定義 (m)
DASH_TRIGGER_DISTANCE: float = 800.0  # ブーストダッシュ発動距離しきい値 (m)

# 射撃弧制限定数 (Phase 6-1)
DEFAULT_FIRE_ARC_DEG: float = 30.0  # 武器の射撃可能弧デフォルト値 (片側、度)

# 格闘コンボシステム定数 (Phase C)
COMBO_BASE_CHANCE: float = 0.30  # 初回コンボ発生確率（30%）
COMBO_CHAIN_DECAY: float = 0.50  # 2連目以降のコンボ継続確率倍率
COMBO_DAMAGE_MULTIPLIER: float = 1.5  # コンボ命中1回あたりのダメージ倍率
COMBO_MAX_CHAIN: int = 3  # 最大コンボ連続回数

# 命中率距離補正定数 (Phase C)
MELEE_CLOSE_ACCURACY_BONUS: float = (
    1.5  # 近接/格闘武器: d <= MELEE_RANGE 時の命中ボーナス
)
MELEE_MID_ACCURACY_BONUS: float = (
    1.2  # 近接/格闘武器: d <= CLOSE_RANGE 時の命中ボーナス
)
RANGED_CLOSE_ACCURACY_PENALTY: float = (
    0.4  # 遠距離武器: d <= MELEE_RANGE 時の命中ペナルティ
)
RANGED_MID_ACCURACY_PENALTY: float = (
    0.7  # 遠距離武器: d <= CLOSE_RANGE 時の命中ペナルティ
)

# 戦略遷移しきい値定数 (Phase 4-3) — ゲームバランス調整用
# AGGRESSIVE → RETREAT (T01)
AGGRESSIVE_RETREAT_HP_THRESHOLD: float = 0.30
AGGRESSIVE_RETREAT_ALIVE_THRESHOLD: float = 0.50
# AGGRESSIVE → DEFENSIVE (T02)
AGGRESSIVE_DEFENSIVE_HP_THRESHOLD: float = 0.50
AGGRESSIVE_DEFENSIVE_ALIVE_THRESHOLD: float = 0.60
# DEFENSIVE → RETREAT (T03)
DEFENSIVE_RETREAT_HP_THRESHOLD: float = 0.25
DEFENSIVE_RETREAT_ALIVE_THRESHOLD: float = 0.40
# DEFENSIVE → AGGRESSIVE (T04)
DEFENSIVE_AGGRESSIVE_HP_THRESHOLD: float = 0.65
DEFENSIVE_AGGRESSIVE_ALIVE_THRESHOLD: float = 0.70
# SNIPER → RETREAT (T05)
SNIPER_RETREAT_HP_THRESHOLD: float = 0.30
SNIPER_RETREAT_ALIVE_THRESHOLD: float = 0.50
# SNIPER → DEFENSIVE (T06)
SNIPER_DEFENSIVE_HP_THRESHOLD: float = 0.50
# ASSAULT → RETREAT (T07)
ASSAULT_RETREAT_HP_THRESHOLD: float = 0.35
ASSAULT_RETREAT_ALIVE_THRESHOLD: float = 0.50
# ASSAULT → AGGRESSIVE (T08)
ASSAULT_AGGRESSIVE_HP_THRESHOLD: float = 0.55
# RETREAT (T09) — 撤退中の維持しきい値
RETREAT_WIPE_ALIVE_THRESHOLD: float = 0.20
