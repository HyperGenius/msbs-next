"""Tests for the Hit-and-Away action pattern (Issue #368 A-2).

HIT_AND_AWAY の3フェーズ（接近→攻撃→離脱）・EN不足フォールバック・
ファジィルール選択を検証する。
"""

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_weapon(range_: float = 500.0, is_melee: bool = False) -> Weapon:
    return Weapon(
        id="test_weapon",
        name="Test Weapon",
        power=10,
        range=range_,
        accuracy=80,
        is_melee=is_melee,
        max_ammo=100,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    max_speed: float = 80.0,
    acceleration: float = 30.0,
    deceleration: float = 50.0,
    max_turn_rate: float = 360.0,
    weapon_range: float = 500.0,
    max_hp: int = 1000,
    current_hp: int = 1000,
    max_en: int = 1000,
    sensor_range: float = 5000.0,
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=current_hp,
        armor=0,
        mobility=1.0,
        position=position,
        weapons=[_make_weapon(weapon_range)],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_speed=max_speed,
        acceleration=acceleration,
        deceleration=deceleration,
        max_turn_rate=max_turn_rate,
        max_en=max_en,
        en_recovery=0,
        sensor_range=sensor_range,
    )


# ---------------------------------------------------------------------------
# フェーズ①: 射程外では接近移動すること
# ---------------------------------------------------------------------------


def test_hit_and_away_approaches_when_out_of_range() -> None:
    """射程外のターゲットに対して HIT_AND_AWAY は接近移動すること."""
    # マップ中央付近に配置（境界斥力の影響を排除するため）
    # 武器射程 200m、ターゲットは 500m 先に配置
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=500, y=0, z=500), weapon_range=200.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=1000, y=0, z=500))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    # ターゲットを発見済みにする
    sim.team_detected_units[player.team_id] = {enemy.id}
    sim.unit_resources[uid]["current_action"] = "HIT_AND_AWAY"
    sim.unit_resources[uid]["current_target_id"] = str(enemy.id)

    initial_x = player.position.x

    # 1ステップ実行
    sim._action_phase(player, dt=0.1)

    new_x = player.position.x
    # プレイヤーが敵方向（+X）に近づいていること
    assert new_x > initial_x, (
        f"射程外では敵に接近するはず: {initial_x:.2f} → {new_x:.2f}"
    )


# ---------------------------------------------------------------------------
# フェーズ②③: 射程内では攻撃後に離脱すること
# ---------------------------------------------------------------------------


def test_hit_and_away_attacks_and_retreats_when_in_range() -> None:
    """射程内のターゲットに対して HIT_AND_AWAY は攻撃後に離脱移動すること."""
    # マップ中央付近に配置（境界斥力の影響を排除するため）
    # 武器射程 500m、ターゲットは 100m 先（+X方向）に配置（射程内）
    # max_turn_rate を極大に設定して 1ステップで即座に方向転換できるようにする
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=500, y=0, z=500),
        weapon_range=500.0,
        acceleration=300.0,
        max_turn_rate=36000.0,  # 即時方向転換で離脱挙動を確認
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=600, y=0, z=500))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    sim.team_detected_units[player.team_id] = {enemy.id}
    sim.unit_resources[uid]["current_action"] = "HIT_AND_AWAY"

    initial_x = player.position.x

    # 攻撃ログが記録されること
    log_count_before = len(sim.logs)
    sim._action_phase(player, dt=0.1)

    attack_logs = [
        lg
        for lg in sim.logs[log_count_before:]
        if lg.actor_id == player.id and lg.action_type in ("ATTACK", "MISS", "WAIT")
    ]
    assert len(attack_logs) > 0, (
        "射程内なら攻撃ログ（ATTACK/MISS/WAIT）が記録されるべき"
    )

    # 離脱: プレイヤーが敵（+X方向）から遠ざかる方向（-X方向）に移動していること
    new_x = player.position.x
    assert new_x < initial_x, (
        f"攻撃後は敵（+X）から離れるはず: {initial_x:.2f} → {new_x:.2f}"
    )


# ---------------------------------------------------------------------------
# EN 不足フォールバック
# ---------------------------------------------------------------------------


def test_hit_and_away_falls_back_to_attack_when_en_low() -> None:
    """EN が低い場合 HIT_AND_AWAY は ATTACK にフォールバックすること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=200, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    # EN をほぼゼロに設定
    sim.unit_resources[uid]["current_en"] = 5

    resolved = sim._resolve_final_action("HIT_AND_AWAY", uid, "AGGRESSIVE")
    assert resolved == "ATTACK", (
        f"EN不足時は ATTACK にフォールバックするべき、実際: {resolved}"
    )


def test_hit_and_away_not_fallen_back_when_en_sufficient() -> None:
    """EN が十分な場合 HIT_AND_AWAY は変更されないこと."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=200, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    sim.unit_resources[uid]["current_en"] = 1000

    resolved = sim._resolve_final_action("HIT_AND_AWAY", uid, "AGGRESSIVE")
    assert resolved == "HIT_AND_AWAY", (
        f"EN十分なら HIT_AND_AWAY を維持するべき、実際: {resolved}"
    )


# ---------------------------------------------------------------------------
# velocity_snapshot が攻撃ログに記録されること
# ---------------------------------------------------------------------------


def test_attack_log_has_velocity_snapshot() -> None:
    """攻撃ログ（ATTACK/MISS）に velocity_snapshot が記録されること."""
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0), weapon_range=500.0
    )
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=100, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    uid = str(player.id)
    sim.team_detected_units[player.team_id] = {enemy.id}
    # ATTACK アクションで攻撃を発生させる
    sim.unit_resources[uid]["current_action"] = "ATTACK"
    sim.unit_resources[uid]["current_target_id"] = str(enemy.id)
    # ランダム命中を確実にするため accuracy を最大に設定
    player.weapons[0].accuracy = 100

    log_count_before = len(sim.logs)
    sim._action_phase(player, dt=0.1)

    combat_logs = [
        lg
        for lg in sim.logs[log_count_before:]
        if lg.actor_id == player.id and lg.action_type in ("ATTACK", "MISS")
    ]
    assert len(combat_logs) > 0, "ATTACK/MISS ログが記録されるべき"
    for lg in combat_logs:
        assert lg.velocity_snapshot is not None, (
            f"action_type={lg.action_type} ログに velocity_snapshot が設定されるべき"
        )


# ---------------------------------------------------------------------------
# ファジィルール: AGGRESSIVE 戦略で HIT_AND_AWAY が選択されること
# ---------------------------------------------------------------------------


def test_aggressive_fuzzy_engine_has_hit_and_away_action() -> None:
    """AGGRESSIVE 戦略のファジィエンジンに HIT_AND_AWAY アクションが定義されていること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=0, y=0, z=0))
    enemy = _make_unit("Enemy", "ENEMY", "ET", Vector3(x=100, y=0, z=0))
    sim = BattleSimulator(player, [enemy])

    # _strategy_engines プロパティから AGGRESSIVE の behavior_selection エンジンを取得
    aggressive_engines = sim._strategy_engines.get("AGGRESSIVE")
    assert aggressive_engines is not None, "AGGRESSIVE エンジンが存在するべき"

    behavior_engine = aggressive_engines.get("behavior")
    assert behavior_engine is not None, "behavior エンジンが存在するべき"

    # HIT_AND_AWAY がメンバーシップ関数に登録されていること
    action_mfs = behavior_engine.rule_set.membership_functions.get("action", {})
    assert "HIT_AND_AWAY" in action_mfs, (
        "AGGRESSIVE エンジンの action MF に HIT_AND_AWAY が定義されているべき"
    )
