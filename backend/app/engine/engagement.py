# backend/app/engine/engagement.py
"""交戦記録と、そこから求める膠着度・優勢度.

戦闘エンジンの状態（`unit_resources`）には依存しない。
記録の持ち主は `unit_resources[unit_id]["engagement"]` に置く。
"""

from dataclasses import dataclass

from app.engine.constants import (
    ENGAGEMENT_RECORD_RANGE,
    ENGAGEMENT_RECORD_RESET_SEC,
    STALEMATE_DOMINANCE_EVEN,
    STALEMATE_DOMINANCE_LIMIT,
    STALEMATE_FULL_ATTACKS,
    STALEMATE_FULL_ELAPSED_SEC,
)


@dataclass
class EngagementRecord:
    """1 体の相手との交戦記録.

    相手が `ENGAGEMENT_RECORD_RANGE` 以内に入った時刻から数える。
    """

    opponent_id: str
    started_at: float
    last_in_range_at: float
    last_hit_at: float | None = None
    attacks_since_hit: int = 0
    attacks: int = 0
    hits: int = 0
    attacked: int = 0
    attacked_hits: int = 0
    damage_dealt: int = 0
    damage_taken: int = 0


@dataclass
class DisengageState:
    """実行中の仕切り直し."""

    opponent_id: str
    started_at: float
    target_distance: float


def track_engagement(
    record: EngagementRecord | None,
    opponent_id: str,
    distance: float,
    now: float,
) -> EngagementRecord | None:
    """現在のターゲットとの距離から、交戦記録を始める・続ける・捨てる.

    ターゲットが変わったら記録を捨てる。多対多では、現在のターゲットとの記録だけを持つ。

    Returns:
        更新後の記録。交戦していなければ None。
    """
    if record is not None and record.opponent_id != opponent_id:
        record = None

    if distance <= ENGAGEMENT_RECORD_RANGE:
        if record is None:
            return EngagementRecord(
                opponent_id=opponent_id, started_at=now, last_in_range_at=now
            )
        record.last_in_range_at = now
        return record

    if (
        record is not None
        and now - record.last_in_range_at >= ENGAGEMENT_RECORD_RESET_SEC
    ):
        return None
    return record


def record_attack(
    attacker_record: EngagementRecord | None,
    defender_record: EngagementRecord | None,
    attacker_id: str,
    defender_id: str,
    damage: int,
    now: float,
) -> None:
    """1 回の攻撃を、攻撃側と防御側の記録に加える.

    相手が記録の相手と一致する側だけを更新する。命中はダメージが入った攻撃とする。
    攻撃側が命中させたら、攻撃側の「最後の命中から」の数え直しを始める。
    """
    is_hit = damage > 0
    if attacker_record is not None and attacker_record.opponent_id == defender_id:
        attacker_record.attacks += 1
        attacker_record.attacks_since_hit += 1
        attacker_record.hits += int(is_hit)
        attacker_record.damage_dealt += damage
        if is_hit:
            attacker_record.last_hit_at = now
            attacker_record.attacks_since_hit = 0
    if defender_record is not None and defender_record.opponent_id == attacker_id:
        defender_record.attacked += 1
        defender_record.attacked_hits += int(is_hit)
        defender_record.damage_taken += damage


def restart_bout(record: EngagementRecord) -> None:
    """攻防の累計を 0 に戻し、優勢度を数え直す.

    最後の命中からの攻撃回数と経過時間は残す。膠着の数えを途切れさせないため。
    """
    record.attacks = 0
    record.hits = 0
    record.attacked = 0
    record.attacked_hits = 0
    record.damage_dealt = 0
    record.damage_taken = 0


def dominance(
    record: EngagementRecord | None, own_max_hp: int, opponent_max_hp: int
) -> float:
    """優勢度を -1〜1 で返す.

    相手に与えた割合（与ダメ ÷ 相手の最大 HP）から、自分が受けた割合を引く。
    正なら優勢。記録が無ければ 0。
    """
    if record is None:
        return 0.0
    dealt = record.damage_dealt / max(1, opponent_max_hp)
    taken = record.damage_taken / max(1, own_max_hp)
    return max(-1.0, min(1.0, dealt - taken))


def stalemate(
    record: EngagementRecord | None,
    now: float,
    own_max_hp: int,
    opponent_max_hp: int,
    patience: float = 1.0,
) -> float:
    """膠着度を 0〜1 で返す.

    攻撃回数・経過時間・互角さの 3 つのうち、最も低いものを使う。
    3 つがそろったときだけ高くするため。記録が無ければ 0。
    攻撃回数と経過時間は、自分の最後の命中から数える。
    相手だけが命中させている場合は、優勢度の低下として扱う。
    `patience` は、膠着度が最大になる攻撃回数と経過時間に掛ける倍率。大きいほど粘る。
    """
    if record is None:
        return 0.0
    since = record.started_at if record.last_hit_at is None else record.last_hit_at
    attacks = min(1.0, record.attacks_since_hit / (STALEMATE_FULL_ATTACKS * patience))
    elapsed = min(1.0, (now - since) / (STALEMATE_FULL_ELAPSED_SEC * patience))
    gap = abs(dominance(record, own_max_hp, opponent_max_hp))
    evenness = 1.0 - (gap - STALEMATE_DOMINANCE_EVEN) / (
        STALEMATE_DOMINANCE_LIMIT - STALEMATE_DOMINANCE_EVEN
    )
    return min(attacks, elapsed, max(0.0, min(1.0, evenness)))
