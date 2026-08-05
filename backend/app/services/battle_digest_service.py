# backend/app/services/battle_digest_service.py
"""BattleResult 生成時に戦闘ダイジェストを計算する共通ヘルパー.

BattleResult の生成箇所は `main.py`（ソロミッション）と
`scripts/run_batch.py`（バッチ/ルーム戦）の2箇所ある。ダイジェスト計算の
グルーコード（直前の一言ログ取得 → 集計 → タグ・文言選出）をそれぞれに
個別実装すると、片方だけ更新してもう片方が更新漏れになる事故が起きる
（実際にIssue #415で発生した）。新しく `BattleResult` の生成箇所を追加する
場合は、必ず `compute_battle_digest_fields` を経由すること。
"""

from sqlmodel import Session, desc, select

from app.engine.battle_digest import build_digest, compute_digest_stats
from app.models.models import BattleLog, BattleResult, MobileSuit


def get_previous_digest_text(session: Session, user_id: str | None) -> str | None:
    """ユーザーの直前のバトルの一言ログを取得する（連続選出回避用）."""
    if not user_id:
        return None
    prev_battle = session.exec(
        select(BattleResult)
        .where(BattleResult.user_id == user_id)
        .order_by(desc(BattleResult.created_at))
        .limit(1)
    ).first()
    return prev_battle.digest_text if prev_battle else None


def compute_battle_digest_fields(
    session: Session,
    user_id: str | None,
    player: MobileSuit,
    logs: list[BattleLog],
    kills: int,
    win_loss: str,
    steps_used: int,
    max_steps: int,
) -> dict:
    """BattleResultに設定するダイジェスト関連フィールドをまとめて計算する.

    Args:
        session: DBセッション（直前の一言ログ取得に使用）
        user_id: バトル結果の所有ユーザーID（未ログイン時はNone）
        player: 集計対象ユニット（バトル後の最終状態が反映されたもの。
            エントリー時点のスナップショットではなく、シミュレーションで
            実際にミューテートされたオブジェクトを渡すこと）
        logs: バトルの全ログ
        kills: 撃墜数
        win_loss: "WIN" / "LOSE" / "DRAW"
        steps_used: シミュレーションが消費したステップ数
        max_steps: シミュレーションの最大ステップ数

    Returns:
        `BattleResult(...)` にそのまま **展開できる dict
        （player_survived, min_hp_percent, damage_severity,
        damage_taken_count, max_hit_damage, dodge_count,
        attacks_received_count, pilot_ms_name, digest_tag, digest_text）
    """
    stats = compute_digest_stats(
        player=player,
        logs=logs,
        kills=kills,
        win_loss=win_loss,
        steps_used=steps_used,
        max_steps=max_steps,
    )
    avoid_text = get_previous_digest_text(session, user_id)
    digest_tag, digest_text = build_digest(stats, avoid_text=avoid_text)

    return {
        "player_survived": stats.player_survived,
        "min_hp_percent": stats.min_hp_percent,
        "damage_severity": stats.damage_severity,
        "damage_taken_count": stats.damage_taken_count,
        "max_hit_damage": stats.max_hit_damage,
        "dodge_count": stats.dodge_count,
        "attacks_received_count": stats.attacks_received_count,
        "pilot_ms_name": stats.pilot_ms_name,
        "digest_tag": digest_tag,
        "digest_text": digest_text,
    }
