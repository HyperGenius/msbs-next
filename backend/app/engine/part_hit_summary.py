# backend/app/engine/part_hit_summary.py
"""バトルログを部位別・武器スロット別に集計する (Issue #504 Phase 3).

Issue #501（部位別フィードバック導入）の最終目的である改造判断への活用に向けて、
「プレイヤーがどの部位に被弾したか」「プレイヤーのどの武器スロットが命中させたか」
をバトル終了時に一度だけ集計し、`BattleResult` の非正規化カラムとして保存する
（`app/engine/battle_digest.py` と同じ「書き込み時に1回だけ計算する」パターン）。
"""

from app.models.models import BattleLog, MobileSuit

# 部位別集計・武器スロット別集計を必要とする action_type
# （ATTACK: 通常命中, MELEE_COMBO: 格闘コンボの追撃）
_HIT_ACTION_TYPES = ("ATTACK", "MELEE_COMBO")


def compute_part_hit_summary(player: MobileSuit, logs: list[BattleLog]) -> dict:
    """プレイヤー視点で部位別の被弾・命中データを集計する.

    既存ログ（`hit_part`/`weapon_slot_role` が未設定のもの）は該当する集計から
    単純に除外される（後方互換性: 集計結果が空になるだけで例外は発生しない）。

    Args:
        player: 集計対象ユニット（バトル後の最終状態が反映されたもの）
        logs: バトルの全ログ

    Returns:
        {
            "taken": {部位名: {"hits": 被弾回数, "damage": 被ダメージ合計}, ...},
            "dealt": {武器スロットロール: {"hits": 命中回数, "damage": 与ダメージ合計}, ...},
        }
    """
    taken: dict[str, dict[str, int]] = {}
    dealt: dict[str, dict[str, int]] = {}

    for log in logs:
        if log.action_type not in _HIT_ACTION_TYPES:
            continue

        if log.target_id == player.id and log.hit_part:
            entry = taken.setdefault(log.hit_part, {"hits": 0, "damage": 0})
            entry["hits"] += 1
            entry["damage"] += log.damage or 0

        if log.actor_id == player.id and log.weapon_slot_role:
            entry = dealt.setdefault(log.weapon_slot_role, {"hits": 0, "damage": 0})
            entry["hits"] += 1
            entry["damage"] += log.damage or 0

    return {"taken": taken, "dealt": dealt}
