# backend/app/engine/engagement_style.py
"""戦術設定（tactics.range）とパイロット能力から、交戦挙動の補正値を求める.

戦闘エンジンの状態（`unit_resources`）には依存しない。
補正の表は `constants.py` に置く。表に無い設定は補正しない。
"""

from app.engine.calculator import PilotStats
from app.engine.constants import (
    PILOT_INT_CAUTION_MAX,
    PILOT_INT_CAUTION_PER_POINT,
    PILOT_MEL_PATIENCE_MAX,
    PILOT_MEL_PATIENCE_PER_POINT,
    PILOT_REF_DISENGAGE_SEC_REDUCTION_MAX,
    PILOT_REF_DISENGAGE_SEC_REDUCTION_PER_POINT,
    PILOT_REF_DISENGAGE_TURN_MAX,
    PILOT_REF_DISENGAGE_TURN_PER_POINT,
    TACTICS_MELEE_WEAPON_SCORE_BIAS,
    TACTICS_RANGED_PREFERENCE_MULTIPLIERS,
    TACTICS_RANGES,
    TACTICS_STALEMATE_PATIENCE,
)
from app.models.models import MobileSuit

DEFAULT_TACTICS_RANGE = "BALANCED"


def tactics_range(unit: MobileSuit) -> str:
    """機体の `tactics.range` を返す. 未設定と許容値外は BALANCED とする."""
    value = (unit.tactics or {}).get("range", DEFAULT_TACTICS_RANGE)
    return value if value in TACTICS_RANGES else DEFAULT_TACTICS_RANGE


def _bonus(stat: int, per_point: float, limit: float) -> float:
    return max(0.0, min(stat * per_point, limit))


def stalemate_patience(range_setting: str, pilot: PilotStats) -> float:
    """膠着とみなすまでの攻撃回数と経過時間に掛ける倍率を返す. 大きいほど粘る."""
    base = TACTICS_STALEMATE_PATIENCE.get(range_setting, 1.0)
    return base * (
        1.0 + _bonus(pilot.mel, PILOT_MEL_PATIENCE_PER_POINT, PILOT_MEL_PATIENCE_MAX)
    )


def perceived_dominance(value: float, pilot: PilotStats) -> float:
    """離脱判断に使う優勢度を返す.

    INT が高いほど劣勢を大きく見積もる。優勢と互角は変えない。
    """
    if value >= 0.0:
        return value
    caution = _bonus(pilot.intel, PILOT_INT_CAUTION_PER_POINT, PILOT_INT_CAUTION_MAX)
    return max(-1.0, value * (1.0 + caution))


def ranged_preference_multiplier(range_setting: str) -> float:
    """仕切り直しの後に射撃武器を優先する時間に掛ける倍率を返す."""
    return TACTICS_RANGED_PREFERENCE_MULTIPLIERS.get(range_setting, 1.0)


def melee_weapon_score_bias(range_setting: str) -> float:
    """武器選択で格闘武器のスコアに足す値を返す."""
    return TACTICS_MELEE_WEAPON_SCORE_BIAS.get(range_setting, 0.0)


def disengage_max_sec(base_sec: float, pilot: PilotStats) -> float:
    """仕切り直しの最長時間を返す. REF が高いほど短い."""
    reduction = _bonus(
        pilot.ref,
        PILOT_REF_DISENGAGE_SEC_REDUCTION_PER_POINT,
        PILOT_REF_DISENGAGE_SEC_REDUCTION_MAX,
    )
    return base_sec * (1.0 - reduction)


def disengage_turn_multiplier(pilot: PilotStats) -> float:
    """仕切り直し中の旋回速度の倍率を返す. REF が高いほど速く向きを変える."""
    return 1.0 + _bonus(
        pilot.ref, PILOT_REF_DISENGAGE_TURN_PER_POINT, PILOT_REF_DISENGAGE_TURN_MAX
    )
