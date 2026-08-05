"""Tests for battle digest tagging and template generation (Issue #415)."""

import uuid

from app.engine.battle_digest import (
    TEMPLATE_POOLS,
    build_digest,
    compute_digest_stats,
    determine_tag,
)
from app.models.models import BattleLog, MobileSuit, Vector3


def create_player(current_hp: int = 1000, max_hp: int = 1000) -> MobileSuit:
    """テスト用のプレイヤー機体を生成する."""
    return MobileSuit(
        name="Gelgoog",
        max_hp=max_hp,
        current_hp=current_hp,
        side="PLAYER",
    )


def make_log(
    actor_id: uuid.UUID,
    action_type: str,
    target_id: uuid.UUID | None = None,
    damage: int | None = None,
    target_max_hp: int | None = None,
    weapon_name: str | None = None,
) -> BattleLog:
    """テスト用の BattleLog を生成する."""
    return BattleLog(
        timestamp=0.0,
        actor_id=actor_id,
        action_type=action_type,
        target_id=target_id,
        damage=damage,
        message="test",
        position_snapshot=Vector3(x=0, y=0, z=0),
        target_max_hp=target_max_hp,
        weapon_name=weapon_name,
    )


def test_compute_digest_stats_no_damage_taken():
    """被弾なしで勝利した場合、damage_severity は無傷になる."""
    player = create_player(current_hp=1000, max_hp=1000)
    stats = compute_digest_stats(
        player=player, logs=[], kills=1, win_loss="WIN", steps_used=10, max_steps=50
    )
    assert stats.player_survived is True
    assert stats.min_hp_percent == 100
    assert stats.damage_severity == "無傷"
    assert stats.damage_taken_count == 0


def test_compute_digest_stats_aggregates_damage_and_dodge():
    """被弾・回避・与ダメージ・使用武器がログから正しく集計される."""
    player = create_player(current_hp=800, max_hp=1000)
    enemy_id = uuid.uuid4()

    logs = [
        make_log(
            enemy_id, "ATTACK", target_id=player.id, damage=100, target_max_hp=1000
        ),
        make_log(enemy_id, "MISS", target_id=player.id),
        make_log(enemy_id, "MISS", target_id=player.id),
        make_log(
            player.id,
            "ATTACK",
            target_id=enemy_id,
            damage=500,
            target_max_hp=1000,
            weapon_name="ビームライフル",
        ),
        make_log(
            player.id,
            "ATTACK",
            target_id=enemy_id,
            damage=100,
            target_max_hp=1000,
            weapon_name="ビームライフル",
        ),
    ]

    stats = compute_digest_stats(
        player=player, logs=logs, kills=1, win_loss="WIN", steps_used=10, max_steps=50
    )

    assert stats.damage_taken_count == 1
    assert stats.dodge_count == 2
    assert stats.attacks_received_count == 3
    assert stats.max_hit_damage == 500
    assert stats.max_hit_ratio == 0.5
    assert stats.signature_weapon_name == "ビームライフル"
    assert stats.damage_severity == "軽微"


def test_determine_tag_shinshou_has_top_priority():
    """辛勝の条件（HP20%未満）は完封の条件も満たしうるが、辛勝が優先される."""
    player = create_player(current_hp=100, max_hp=1000)  # 10%
    stats = compute_digest_stats(
        player=player, logs=[], kills=1, win_loss="WIN", steps_used=10, max_steps=50
    )
    assert determine_tag(stats) == "辛勝"


def test_determine_tag_zenmetsu():
    """撃破数5体以上（かつ被弾あり・HP十分）は殲滅と判定される."""
    player = create_player(current_hp=900, max_hp=1000)
    enemy_id = uuid.uuid4()
    logs = [
        make_log(
            enemy_id, "ATTACK", target_id=player.id, damage=100, target_max_hp=1000
        )
    ]
    stats = compute_digest_stats(
        player=player, logs=logs, kills=5, win_loss="WIN", steps_used=10, max_steps=50
    )
    assert determine_tag(stats) == "殲滅"


def test_determine_tag_isseki_hissatsu():
    """一撃が対象最大HPの40%以上を占める場合、一撃必殺と判定される."""
    player = create_player(current_hp=900, max_hp=1000)
    enemy_id = uuid.uuid4()
    logs = [
        make_log(
            enemy_id, "ATTACK", target_id=player.id, damage=100, target_max_hp=1000
        ),
        make_log(
            player.id, "ATTACK", target_id=enemy_id, damage=450, target_max_hp=1000
        ),
    ]
    stats = compute_digest_stats(
        player=player, logs=logs, kills=1, win_loss="WIN", steps_used=10, max_steps=50
    )
    assert determine_tag(stats) == "一撃必殺"


def test_determine_tag_choukisen():
    """消費ステップ比率が高い（早期決着しなかった）場合、長期戦と判定される."""
    player = create_player(current_hp=900, max_hp=1000)
    enemy_id = uuid.uuid4()
    logs = [
        make_log(
            enemy_id, "ATTACK", target_id=player.id, damage=100, target_max_hp=1000
        )
    ]
    stats = compute_digest_stats(
        player=player, logs=logs, kills=1, win_loss="WIN", steps_used=40, max_steps=50
    )
    assert determine_tag(stats) == "長期戦"


def test_determine_tag_kaihi_tokka():
    """被攻撃回数のうち半分以上を回避した場合、回避特化と判定される."""
    player = create_player(current_hp=900, max_hp=1000)
    enemy_id = uuid.uuid4()
    logs = [
        make_log(
            enemy_id, "ATTACK", target_id=player.id, damage=100, target_max_hp=1000
        ),
        make_log(enemy_id, "MISS", target_id=player.id),
        make_log(enemy_id, "MISS", target_id=player.id),
    ]
    stats = compute_digest_stats(
        player=player, logs=logs, kills=1, win_loss="WIN", steps_used=10, max_steps=50
    )
    assert determine_tag(stats) == "回避特化"


def test_determine_tag_normal_fallback():
    """いずれの条件にも該当しない勝利は通常と判定される."""
    player = create_player(current_hp=900, max_hp=1000)
    enemy_id = uuid.uuid4()
    logs = [
        make_log(
            enemy_id, "ATTACK", target_id=player.id, damage=100, target_max_hp=1000
        )
    ]
    stats = compute_digest_stats(
        player=player, logs=logs, kills=1, win_loss="WIN", steps_used=10, max_steps=50
    )
    assert determine_tag(stats) == "通常"


def test_determine_tag_lose_with_kills():
    """敗北しつつ1体以上撃破していれば力戦及ばずと判定される."""
    player = create_player(current_hp=0, max_hp=1000)
    stats = compute_digest_stats(
        player=player, logs=[], kills=1, win_loss="LOSE", steps_used=10, max_steps=50
    )
    assert stats.player_survived is False
    assert stats.damage_severity == "撃墜"
    assert determine_tag(stats) == "力戦及ばず"


def test_determine_tag_lose_without_kills():
    """1体も撃破せず敗北した場合は完敗と判定される."""
    player = create_player(current_hp=0, max_hp=1000)
    stats = compute_digest_stats(
        player=player, logs=[], kills=0, win_loss="LOSE", steps_used=10, max_steps=50
    )
    assert determine_tag(stats) == "完敗"


def test_determine_tag_draw():
    """引き分けは常に痛み分けと判定される."""
    player = create_player(current_hp=500, max_hp=1000)
    stats = compute_digest_stats(
        player=player, logs=[], kills=0, win_loss="DRAW", steps_used=50, max_steps=50
    )
    assert determine_tag(stats) == "痛み分け"


def test_build_digest_renders_placeholders():
    """build_digest はタグに応じたテンプレートを埋め込んだ文字列を返す."""
    player = create_player(current_hp=100, max_hp=1000)  # 辛勝
    stats = compute_digest_stats(
        player=player, logs=[], kills=1, win_loss="WIN", steps_used=10, max_steps=50
    )
    tag, text = build_digest(stats)
    assert tag == "辛勝"
    assert text in [t.format(ms_name="Gelgoog", min_hp=10) for t in TEMPLATE_POOLS[tag]]


def test_build_digest_avoids_immediate_repeat():
    """avoid_text と同じ文言が候補に複数ある場合、別の候補が選ばれる."""
    player = create_player(current_hp=100, max_hp=1000)
    stats = compute_digest_stats(
        player=player, logs=[], kills=1, win_loss="WIN", steps_used=10, max_steps=50
    )
    tag = determine_tag(stats)
    avoid_text = TEMPLATE_POOLS[tag][0].format(
        ms_name=stats.pilot_ms_name,
        min_hp=stats.min_hp_percent,
        kills=stats.kills,
        weapon_name="武装",
        max_hit_damage=stats.max_hit_damage,
    )
    for _ in range(20):
        _, text = build_digest(stats, avoid_text=avoid_text)
        assert text != avoid_text
