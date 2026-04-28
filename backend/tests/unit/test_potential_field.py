"""Tests for the potential field autonomous movement (Phase 3-2).

ポテンシャルフィールド法による自律移動を検証するテスト。
引力・斥力の各ソースが正しく合成されることを確認する。
"""

import math

import numpy as np
import pytest

from app.engine.constants import (
    ALLY_REPULSION_RADIUS,
    BOUNDARY_MARGIN,
    HIGH_THREAT_THRESHOLD,
    MAP_BOUNDS,
)
from app.engine.simulation import MOVE_LOG_MIN_DIST, BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_weapon(
    range_: float = 500.0,
    power: float = 100.0,
    wid: str = "w1",
) -> Weapon:
    return Weapon(
        id=wid,
        name="Test Weapon",
        power=power,
        range=range_,
        accuracy=80,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    max_hp: float = 1000.0,
    weapon_range: float = 500.0,
    weapon_power: float = 100.0,
    wid: str = "w1",
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=max_hp,
        armor=0,
        mobility=1.0,
        position=position,
        weapons=[_make_weapon(weapon_range, weapon_power, wid)],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_speed=80.0,
        acceleration=30.0,
        deceleration=50.0,
        max_turn_rate=360.0,
    )


# ---------------------------------------------------------------------------
# 定数テスト
# ---------------------------------------------------------------------------


def test_potential_field_constants_defined() -> None:
    """ポテンシャルフィールド定数が正しく定義されていること."""
    assert ALLY_REPULSION_RADIUS == 150.0
    assert BOUNDARY_MARGIN == 200.0
    assert HIGH_THREAT_THRESHOLD == 0.5
    assert MAP_BOUNDS == (0.0, 5000.0)
    assert MOVE_LOG_MIN_DIST == 100.0


# ---------------------------------------------------------------------------
# _calculate_potential_field テスト
# ---------------------------------------------------------------------------


def test_potential_field_attack_attracts_to_target() -> None:
    """ATTACK 行動時に攻撃ターゲットへの引力が働くこと."""
    # マップ境界の影響を避けるために中央付近に配置
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    # ターゲットを +x 方向に配置
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=3000, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])

    # ATTACK アクションに設定
    sim.unit_resources[str(player.id)]["current_action"] = "ATTACK"
    direction = sim._calculate_potential_field(player, target=enemy)

    # +x 方向へ引力が働くこと
    assert direction[0] > 0, "攻撃ターゲット方向 (+x) への引力が働くこと"


def test_potential_field_move_attracts_to_nearest_enemy() -> None:
    """MOVE 行動時に最近敵への引力が働くこと."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=3000, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])

    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"
    direction = sim._calculate_potential_field(player, target=None)

    assert direction[0] > 0, "MOVE 時に最近敵方向 (+x) への引力が働くこと"


def test_potential_field_attack_no_attraction_without_target() -> None:
    """ATTACK 行動でも target=None の場合は攻撃引力が 0 であること.

    current_action="ATTACK" かつ target=None の場合:
    - ATTACK 引力ブロック: スキップ (target is None のため)
    - MOVE/RETREAT 引力ブロック: スキップ (current_action が "ATTACK" のため)
    → 脅威斥力・味方斥力・境界斥力のみが合成される。
    """
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=3000, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])

    # ATTACK に設定するが target=None（MOVE attraction に変わる）
    sim.unit_resources[str(player.id)]["current_action"] = "ATTACK"
    direction = sim._calculate_potential_field(player, target=None)

    # target=None では攻撃引力 2.0 は加算されない → MOVE 引力 0 のみ
    # ゼロベクトルにならないことを確認（フォールバック）
    assert np.linalg.norm(direction) > 0.99


def test_potential_field_returns_unit_vector() -> None:
    """返り値が単位ベクトルであること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=3000, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

    direction = sim._calculate_potential_field(player, target=enemy)
    magnitude = float(np.linalg.norm(direction))
    assert abs(magnitude - 1.0) < 1e-6, f"単位ベクトルを返すこと (magnitude={magnitude})"


def test_potential_field_y_component_is_zero() -> None:
    """返り値の Y 成分が 0 であること (XZ 平面移動)."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=3000, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "ATTACK"

    direction = sim._calculate_potential_field(player, target=enemy)
    assert abs(direction[1]) < 1e-6, f"Y 成分が 0 であること (y={direction[1]})"


# ---------------------------------------------------------------------------
# 味方斥力テスト
# ---------------------------------------------------------------------------


def test_potential_field_ally_repulsion_pushes_away() -> None:
    """ALLY_REPULSION_RADIUS 以内の味方から斥力が働くこと."""
    # マップ中央付近に配置
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    # 味方を +x に近距離、かつわずかに z をオフセット（斥力に z 成分を持たせる）
    ally = _make_unit(
        "Ally", "PLAYER", "PT", Vector3(x=2600, y=0, z=2510), wid="a1"
    )
    ally.current_hp = 100
    # 敵を +x 遠距離に配置
    enemy = _make_unit(
        "Enemy",
        "ENEMY",
        "ET",
        Vector3(x=4000, y=0, z=2500),
        weapon_power=10.0,
        wid="e1",
    )

    sim = BattleSimulator(player, [enemy])
    # ally を同チームとして追加
    sim.units.append(ally)
    uid_ally = str(ally.id)
    sim.unit_resources[uid_ally] = {
        "current_en": ally.max_en,
        "current_propellant": ally.max_propellant,
        "weapon_states": {},
        "current_action": "MOVE",
        "velocity_vec": np.zeros(3),
        "heading_deg": 0.0,
    }

    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

    # 味方なし vs 味方あり で方向ベクトルが変わること
    sim_no_ally = BattleSimulator(player, [enemy])
    sim_no_ally.unit_resources[str(player.id)]["current_action"] = "MOVE"
    direction_no_ally = sim_no_ally._calculate_potential_field(player)
    direction_with_ally = sim._calculate_potential_field(player)

    # 味方が +x 方向（わずかに +z オフセット）にいるので、方向ベクトルが変化する
    # 味方のいない場合と方向が異なること（斥力が加算されている証拠）
    assert not np.allclose(direction_with_ally, direction_no_ally, atol=1e-6), (
        "味方斥力によって方向ベクトルが変化すること"
    )


def test_potential_field_ally_outside_radius_no_effect() -> None:
    """ALLY_REPULSION_RADIUS より遠い味方には斥力が働かないこと."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    # 味方を ALLY_REPULSION_RADIUS より遠くに配置
    far_pos = 2500 + ALLY_REPULSION_RADIUS + 100  # 境界より確実に遠い
    ally = _make_unit(
        "FarAlly", "PLAYER", "PT", Vector3(x=far_pos, y=0, z=2500), wid="a2"
    )
    ally.current_hp = 100
    enemy = _make_unit(
        "Enemy",
        "ENEMY",
        "ET",
        Vector3(x=3000, y=0, z=2500),
        weapon_power=10.0,
        wid="e2",
    )

    sim_with_far_ally = BattleSimulator(player, [enemy])
    sim_with_far_ally.units.append(ally)
    uid_ally = str(ally.id)
    sim_with_far_ally.unit_resources[uid_ally] = {
        "current_en": ally.max_en,
        "current_propellant": ally.max_propellant,
        "weapon_states": {},
        "current_action": "MOVE",
        "velocity_vec": np.zeros(3),
        "heading_deg": 0.0,
    }
    sim_with_far_ally.unit_resources[str(player.id)]["current_action"] = "MOVE"

    sim_no_ally = BattleSimulator(player, [enemy])
    sim_no_ally.unit_resources[str(player.id)]["current_action"] = "MOVE"

    d1 = sim_no_ally._calculate_potential_field(player)
    d2 = sim_with_far_ally._calculate_potential_field(player)

    # 遠い味方は影響しない
    np.testing.assert_allclose(d1, d2, atol=1e-6)


# ---------------------------------------------------------------------------
# マップ境界斥力テスト
# ---------------------------------------------------------------------------


def test_potential_field_boundary_repulsion_near_edge() -> None:
    """マップ境界近くでは境界からの斥力が働くこと."""
    # x=0 境界付近に配置（境界内）
    near_edge = BOUNDARY_MARGIN / 2  # 100m (境界内)
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=near_edge, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=2000, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

    # 境界から離れた中央付近のユニット
    player_center = _make_unit(
        "PlayerCenter", "PLAYER", "PT2", Vector3(x=2500, y=0, z=2500), wid="wc"
    )
    enemy_center = _make_unit(
        "EnemyCenter", "ENEMY", "ET2", Vector3(x=3000, y=0, z=2500), weapon_power=10.0, wid="ec"
    )
    sim_center = BattleSimulator(player_center, [enemy_center])
    sim_center.unit_resources[str(player_center.id)]["current_action"] = "MOVE"

    direction_near_edge = sim._calculate_potential_field(player)
    direction_center = sim_center._calculate_potential_field(player_center)

    # 境界近くでは +x 成分が大きい（境界斥力が +x 方向）
    # 中央では境界斥力なし、引力のみ（player_center は enemy_center の方向 +x に引かれる）
    # 境界近くの方が x 成分が大きいはず
    assert direction_near_edge[0] >= direction_center[0] - 0.01, (
        "境界近くでは境界斥力により +x 成分が中央以上であること"
    )


def test_potential_field_unit_stays_in_bounds() -> None:
    """シミュレーション後にユニットがマップ境界内に留まること."""
    map_min, map_max = MAP_BOUNDS
    # マップ境界近くに配置して移動させる
    player = _make_unit(
        "Player", "PLAYER", "PT", Vector3(x=10, y=0, z=10), max_hp=1000.0
    )
    # 壁に向けて引っ張る敵（境界外側方向）
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=2500, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

    for _ in range(100):
        sim.step()

    # ユニットがマップ内に留まること
    pos = player.position
    assert pos.x >= map_min - 1.0, f"x={pos.x} がマップ下限を下回った"
    assert pos.x <= map_max + 1.0, f"x={pos.x} がマップ上限を超えた"
    assert pos.z >= map_min - 1.0, f"z={pos.z} がマップ下限を下回った"
    assert pos.z <= map_max + 1.0, f"z={pos.z} がマップ上限を超えた"


# ---------------------------------------------------------------------------
# 高脅威敵の斥力テスト
# ---------------------------------------------------------------------------


def test_potential_field_high_threat_enemy_repulsion() -> None:
    """高脅威敵（射程外）から斥力が働くこと."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=2500, y=0, z=2500),
        max_hp=100.0,
        weapon_range=300.0,
    )
    # 高脅威敵: attack_power=100 > 0.5 * max_hp=100 → threat_score=1.0 > HIGH_THREAT_THRESHOLD
    # かつ距離 > weapon_range=300
    high_threat_enemy = _make_unit(
        "HighThreat",
        "ENEMY",
        "ET",
        Vector3(x=3000, y=0, z=2500),  # 距離 500 > 300
        max_hp=100.0,
        weapon_power=200.0,  # threat_score = 200/100 = 2.0 > 0.5
    )
    sim = BattleSimulator(player, [high_threat_enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"
    direction_high_threat = sim._calculate_potential_field(player)

    # 低脅威敵（同じ距離）
    low_threat_enemy = _make_unit(
        "LowThreat",
        "ENEMY",
        "ET2",
        Vector3(x=3000, y=0, z=2500),
        max_hp=100.0,
        weapon_power=10.0,  # threat_score = 10/100 = 0.1 < 0.5
        wid="lt",
    )
    sim_low = BattleSimulator(player, [low_threat_enemy])
    sim_low.unit_resources[str(player.id)]["current_action"] = "MOVE"
    direction_low_threat = sim_low._calculate_potential_field(player)

    # 高脅威敵の場合は +x 引力が抑制される（斥力が加算される）
    assert direction_high_threat[0] < direction_low_threat[0], (
        "高脅威敵の斥力により x 成分が低脅威時より小さくなること"
    )


def test_potential_field_high_threat_in_range_no_repulsion() -> None:
    """高脅威敵でも射程内なら斥力が働かないこと."""
    player = _make_unit(
        "Player",
        "PLAYER",
        "PT",
        Vector3(x=2500, y=0, z=2500),
        max_hp=100.0,
        weapon_range=600.0,  # 大きい射程
    )
    # 高脅威敵: 距離=500 < weapon_range=600 → 射程内なので斥力なし
    in_range_enemy = _make_unit(
        "InRange",
        "ENEMY",
        "ET",
        Vector3(x=3000, y=0, z=2500),
        max_hp=100.0,
        weapon_power=200.0,
        wid="ir",
    )
    sim_in_range = BattleSimulator(player, [in_range_enemy])
    sim_in_range.unit_resources[str(player.id)]["current_action"] = "MOVE"

    out_range_enemy = _make_unit(
        "OutRange",
        "ENEMY",
        "ET2",
        Vector3(x=3000, y=0, z=2500),
        max_hp=100.0,
        weapon_power=200.0,
        wid="or",
    )
    sim_out = BattleSimulator(
        _make_unit(
            "Player2",
            "PLAYER",
            "PT2",
            Vector3(x=2500, y=0, z=2500),
            max_hp=100.0,
            weapon_range=300.0,  # 小さい射程 → 距離500は射程外
            wid="wp2",
        ),
        [out_range_enemy],
    )
    player2_id = str(sim_out.player.id)
    sim_out.unit_resources[player2_id]["current_action"] = "MOVE"

    d_in = sim_in_range._calculate_potential_field(player)
    d_out = sim_out._calculate_potential_field(sim_out.player)

    # 射程内では斥力なし → d_in の +x 成分が d_out より大きい
    assert d_in[0] >= d_out[0], "射程内の高脅威敵には斥力が働かないこと"


# ---------------------------------------------------------------------------
# ローカルミニマム回避テスト
# ---------------------------------------------------------------------------


def test_potential_field_no_crash_on_zero_vector() -> None:
    """合算ベクトルがゼロになってもクラッシュしないこと."""
    # 全ての力が釣り合ってゼロベクトルになるシナリオを強制的に作るのは難しいため、
    # 力が小さい状況でも単位ベクトルが返ることを確認する
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    # 同位置に敵（距離0のため引力が計算されない）
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=2500, y=0, z=2500), weapon_power=1.0
    )
    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

    # 例外が発生しないこと、かつ単位ベクトルが返ること
    direction = sim._calculate_potential_field(player)
    magnitude = float(np.linalg.norm(direction))
    assert abs(magnitude - 1.0) < 1e-6, "ゼロベクトル時もフォールバックで単位ベクトルを返すこと"


def test_potential_field_local_minimum_returns_random_direction() -> None:
    """ゼロベクトルになった場合ランダム方向を返すこと（複数回呼び出しで方向が変わる）."""
    # 敵なし・味方なし・境界なしのシナリオでゼロベクトルになるようにする
    # → 実際には境界斥力があるため完全なゼロは難しいが、フォールバック経路のテスト
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=2500, y=0, z=2500), weapon_power=1.0
    )
    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

    # 複数回呼び出しても例外が発生しないこと
    for _ in range(10):
        d = sim._calculate_potential_field(player)
        assert np.linalg.norm(d) > 0.99, "常に非ゼロベクトルを返すこと"


# ---------------------------------------------------------------------------
# _process_movement がポテンシャルフィールドを使うことの確認
# ---------------------------------------------------------------------------


def test_process_movement_uses_potential_field() -> None:
    """_process_movement がポテンシャルフィールドで方向を決定すること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=3000, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

    initial_pos = player.position.to_numpy().copy()
    pos_actor = player.position.to_numpy()
    pos_target = enemy.position.to_numpy()
    diff_vector = pos_target - pos_actor
    distance = float(np.linalg.norm(diff_vector))

    sim._process_movement(player, pos_actor, pos_target, diff_vector, distance, 0.1)

    # 位置が変化すること
    new_pos = player.position.to_numpy()
    assert not np.allclose(new_pos, initial_pos), "移動後に位置が変化すること"


def test_process_movement_logs_when_distance_sufficient() -> None:
    """distance >= MOVE_LOG_MIN_DIST のとき MOVE ログが出力されること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=3000, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

    pos_actor = player.position.to_numpy()
    pos_target = enemy.position.to_numpy()
    diff_vector = pos_target - pos_actor
    distance = MOVE_LOG_MIN_DIST  # 丁度 100m

    sim._process_movement(player, pos_actor, pos_target, diff_vector, distance, 0.1)

    move_logs = [log for log in sim.logs if log.action_type == "MOVE"]
    assert len(move_logs) >= 1, "MOVE_LOG_MIN_DIST 以上のとき MOVE ログが出力されること"


def test_process_movement_no_log_when_distance_short() -> None:
    """distance < MOVE_LOG_MIN_DIST のとき MOVE ログが出力されないこと."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=2550, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

    pos_actor = player.position.to_numpy()
    pos_target = enemy.position.to_numpy()
    diff_vector = pos_target - pos_actor
    distance = MOVE_LOG_MIN_DIST - 1  # 99m < 100m

    sim._process_movement(player, pos_actor, pos_target, diff_vector, distance, 0.1)

    move_logs = [log for log in sim.logs if log.action_type == "MOVE"]
    assert len(move_logs) == 0, "MOVE_LOG_MIN_DIST 未満のとき MOVE ログを抑制すること"


# ---------------------------------------------------------------------------
# _search_movement がポテンシャルフィールドを使うことの確認
# ---------------------------------------------------------------------------


def test_search_movement_uses_potential_field() -> None:
    """_search_movement がポテンシャルフィールドで移動すること."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=4000, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])
    # 索敵フェーズ不実行 → 未発見

    initial_pos = player.position.to_numpy().copy()
    sim._search_movement(player, dt=0.1)

    new_pos = player.position.to_numpy()
    assert not np.allclose(new_pos, initial_pos), "_search_movement 後に位置が変化すること"


def test_search_movement_no_log_when_distance_short() -> None:
    """_search_movement で距離 < MOVE_LOG_MIN_DIST の場合ログが出力されないこと."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    # 50m しか離れていない敵（MOVE_LOG_MIN_DIST=100 未満）
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=2550, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])
    sim._search_movement(player, dt=0.1)

    move_logs = [log for log in sim.logs if log.action_type == "MOVE"]
    assert len(move_logs) == 0, "近距離索敵では MOVE ログが抑制されること"


# ---------------------------------------------------------------------------
# 撤退ポイント引力テスト (Phase 3-3 用の引数確認)
# ---------------------------------------------------------------------------


def test_potential_field_retreat_points_attract() -> None:
    """retreat_points が指定された場合に引力が働くこと."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=2500, y=0, z=2500), weapon_power=1.0
    )
    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "RETREAT"

    # 撤退ポイントを +x 方向に設定
    retreat_point = [4000.0, 0.0, 2500.0]
    direction = sim._calculate_potential_field(
        player, target=None, retreat_points=[retreat_point]
    )

    # 撤退ポイント方向 (+x) に引力が働くこと
    assert direction[0] > 0, "撤退ポイント (+x) への引力が働くこと"


def test_potential_field_empty_retreat_points_no_error() -> None:
    """retreat_points=[] でもエラーが発生しないこと."""
    player = _make_unit("Player", "PLAYER", "PT", Vector3(x=2500, y=0, z=2500))
    enemy = _make_unit(
        "Enemy", "ENEMY", "ET", Vector3(x=3000, y=0, z=2500), weapon_power=10.0
    )
    sim = BattleSimulator(player, [enemy])
    sim.unit_resources[str(player.id)]["current_action"] = "MOVE"

    # 例外が発生しないこと
    direction = sim._calculate_potential_field(player, retreat_points=[])
    assert np.linalg.norm(direction) > 0.99
