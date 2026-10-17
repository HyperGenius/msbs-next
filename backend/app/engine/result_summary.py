# backend/app/engine/result_summary.py
"""結果画面の戦果サマリー（被弾部位・武器の命中率・索敵）をログから集計する.

フロントの `useWeaponAccuracySummary.ts`・`useDetectionSummary.ts` と同じ結果を返す。
両者を変えるときは `tests/fixtures/result_summary_parity.json` も更新する。
このファイルの関数は DB を使わない。
"""

from collections.abc import Iterable

from app.engine.part_hit_summary import compute_part_hit_summary
from app.models.models import BattleLog, MobileSuit

_ATTEMPT_ACTION_TYPES = ("ATTACK", "MELEE_COMBO", "MISS")
_HIT_ACTION_TYPES = ("ATTACK", "MELEE_COMBO")
# 武器名の無い攻撃ログは格闘として数える。
_UNNAMED_WEAPON = "格闘"


def compute_weapon_accuracy_summary(
    player_id: str, logs: Iterable[BattleLog], equipped_weapon_names: list[str]
) -> list[dict]:
    """自機の武器ごとの命中数・試行数を、試行数の多い順に返す.

    一度も使わなかった装備武器も 0/0 で含める。
    試行数が同じ武器は、装備順・ログに出た順のまま並べる。
    """
    attempts: dict[str, int] = dict.fromkeys(equipped_weapon_names, 0)
    hits: dict[str, int] = dict.fromkeys(equipped_weapon_names, 0)

    for log in logs:
        if str(log.actor_id) != player_id:
            continue
        if log.action_type not in _ATTEMPT_ACTION_TYPES:
            continue
        weapon_name = (
            log.weapon_name if log.weapon_name is not None else _UNNAMED_WEAPON
        )
        attempts[weapon_name] = attempts.get(weapon_name, 0) + 1
        if log.action_type in _HIT_ACTION_TYPES:
            hits[weapon_name] = hits.get(weapon_name, 0) + 1

    ordered = sorted(attempts, key=lambda name: -attempts[name])
    return [
        {"weapon_name": name, "hits": hits.get(name, 0), "attempts": attempts[name]}
        for name in ordered
    ]


def compute_detection_summary(
    player_id: str, logs: Iterable[BattleLog], enemy_count: int
) -> dict:
    """自機が索敵に成功した敵機の数（重複なし）と、敵機の総数を返す."""
    captured_ids = {
        str(log.target_id)
        for log in logs
        if log.action_type == "DETECTION"
        and str(log.actor_id) == player_id
        and log.target_id is not None
    }
    return {"captured": len(captured_ids), "total": enemy_count}


def compute_result_summary_fields(
    player: MobileSuit, logs: list[BattleLog], enemy_count: int
) -> dict:
    """`BattleResult` に保存する戦果サマリーの項目を返す.

    Args:
        player: 集計する機体。ID と装備武器だけを使う。
        logs: バトルの全ログ
        enemy_count: `enemies_info` の件数。索敵の総数として表示する。
    """
    player_id = str(player.id)
    return {
        "part_hit_summary": compute_part_hit_summary(player=player, logs=logs),
        "weapon_accuracy_summary": compute_weapon_accuracy_summary(
            player_id, logs, [w.name for w in player.weapons]
        ),
        "detection_summary": compute_detection_summary(player_id, logs, enemy_count),
    }
