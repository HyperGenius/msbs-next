"""Tests for app.engine.result_summary."""

import json
import uuid
from pathlib import Path

from app.engine.result_summary import (
    compute_detection_summary,
    compute_result_summary_fields,
    compute_weapon_accuracy_summary,
)
from app.models.models import BattleLog, MobileSuit, Vector3, Weapon

# フロントの tests/unit/resultSummaryParity.test.ts も同じデータを読む。
PARITY_FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "result_summary_parity.json"
)


def _log(
    actor_id: uuid.UUID,
    action_type: str,
    target_id: uuid.UUID | None = None,
    weapon_name: str | None = None,
) -> BattleLog:
    return BattleLog(
        timestamp=0.0,
        actor_id=actor_id,
        action_type=action_type,
        target_id=target_id,
        weapon_name=weapon_name,
        message="test",
        position_snapshot=Vector3(),
    )


def test_matches_frontend_on_shared_logs():
    """フロントの集計と同じ共通データで、同じ結果になる."""
    data = json.loads(PARITY_FIXTURE.read_text(encoding="utf-8"))
    info = data["player_info"]
    player = MobileSuit(
        id=uuid.UUID(info["id"]),
        name=info["name"],
        max_hp=1000,
        current_hp=1000,
        side="PLAYER",
        weapons=[Weapon(**w) for w in info["weapons"]],
    )
    logs = [BattleLog.model_validate(log) for log in data["logs"]]

    fields = compute_result_summary_fields(player, logs, len(data["enemies_info"]))

    assert fields == data["expected"]


def test_weapon_accuracy_includes_unused_equipped_weapons():
    """使わなかった装備武器も 0/0 で残る."""
    player_id = uuid.uuid4()

    summary = compute_weapon_accuracy_summary(str(player_id), [], ["ビームライフル"])

    assert summary == [{"weapon_name": "ビームライフル", "hits": 0, "attempts": 0}]


def test_weapon_accuracy_ignores_other_units_and_non_attack_logs():
    """他機のログと、攻撃以外のログは数えない."""
    player_id = uuid.uuid4()
    enemy_id = uuid.uuid4()
    logs = [
        _log(enemy_id, "ATTACK", player_id, "マシンガン"),
        _log(player_id, "MOVE"),
        _log(player_id, "DETECTION", enemy_id),
    ]

    assert compute_weapon_accuracy_summary(str(player_id), logs, []) == []


def test_detection_counts_each_enemy_once():
    """同じ敵を何度捕捉しても 1 機として数える."""
    player_id = uuid.uuid4()
    enemy_id = uuid.uuid4()
    logs = [
        _log(player_id, "DETECTION", enemy_id),
        _log(player_id, "DETECTION", enemy_id),
        _log(enemy_id, "DETECTION", player_id),
    ]

    summary = compute_detection_summary(str(player_id), logs, enemy_count=2)

    assert summary == {"captured": 1, "total": 2}
