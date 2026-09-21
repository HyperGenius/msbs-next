"""Tests for app.engine.part_hit_summary (Issue #504)."""

import uuid

from app.engine.part_hit_summary import compute_part_hit_summary
from app.models.models import BattleLog, MobileSuit, Vector3


def _make_player() -> MobileSuit:
    return MobileSuit(name="Gelgoog", max_hp=1000, current_hp=1000, side="PLAYER")


def _make_log(
    actor_id: uuid.UUID,
    target_id: uuid.UUID,
    action_type: str = "ATTACK",
    damage: int | None = 100,
    hit_part: str | None = None,
    weapon_slot_role: str | None = None,
) -> BattleLog:
    return BattleLog(
        timestamp=0.0,
        actor_id=actor_id,
        action_type=action_type,
        target_id=target_id,
        damage=damage,
        message="test",
        position_snapshot=Vector3(),
        hit_part=hit_part,
        weapon_slot_role=weapon_slot_role,
    )


def test_aggregates_taken_by_hit_part_and_dealt_by_slot_role():
    """被弾は hit_part 別、命中は weapon_slot_role 別に集計される."""
    player = _make_player()
    enemy_id = uuid.uuid4()
    logs = [
        _make_log(enemy_id, player.id, damage=50, hit_part="HEAD"),
        _make_log(enemy_id, player.id, damage=30, hit_part="HEAD"),
        _make_log(player.id, enemy_id, damage=80, weapon_slot_role="RIGHT_ARM"),
    ]

    summary = compute_part_hit_summary(player, logs)

    assert summary["taken"] == {"HEAD": {"hits": 2, "damage": 80}}
    assert summary["dealt"] == {"RIGHT_ARM": {"hits": 1, "damage": 80}}


def test_ignores_logs_without_hit_part_or_weapon_slot_role():
    """既存ログ（新フィールド未設定）は集計から除外され、空の集計を返す（後方互換性）."""
    player = _make_player()
    enemy_id = uuid.uuid4()
    logs = [
        _make_log(enemy_id, player.id, damage=50),
        _make_log(player.id, enemy_id, damage=80),
    ]

    summary = compute_part_hit_summary(player, logs)

    assert summary == {"taken": {}, "dealt": {}}


def test_ignores_non_hit_action_types():
    """MISS/DESTROYED等はダメージ実績が無いため集計対象外."""
    player = _make_player()
    enemy_id = uuid.uuid4()
    logs = [
        _make_log(
            enemy_id,
            player.id,
            action_type="MISS",
            damage=0,
            hit_part="HEAD",
        ),
    ]

    summary = compute_part_hit_summary(player, logs)

    assert summary == {"taken": {}, "dealt": {}}


def test_only_counts_logs_involving_player():
    """プレイヤーが関与しないログ（NPC同士等）は集計対象外."""
    player = _make_player()
    other_a = uuid.uuid4()
    other_b = uuid.uuid4()
    logs = [
        _make_log(
            other_a, other_b, damage=50, hit_part="HEAD", weapon_slot_role="LEFT_ARM"
        ),
    ]

    summary = compute_part_hit_summary(player, logs)

    assert summary == {"taken": {}, "dealt": {}}
