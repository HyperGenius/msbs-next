#!/usr/bin/env python3
"""シナリオ: scenario_full_field.

6 個の障害物フィールドで 3 チーム戦。
全システム統合動作・ローカルミニマム発生頻度を確認する。

配置 (MAP: 0〜5000):
    チームA (1機): (500, 0, 2500)  — AGGRESSIVE
    チームB (1機): (2500, 0, 500)  — AGGRESSIVE
    チームC (1機): (2500, 0, 4500) — AGGRESSIVE

    障害物 (6個):
        obs1: (1000, 0, 1000)  r=150
        obs2: (2000, 0, 2000)  r=120
        obs3: (3000, 0, 1500)  r=100
        obs4: (1500, 0, 3500)  r=130
        obs5: (3500, 0, 3000)  r=110
        obs6: (2500, 0, 2500)  r=140  (フィールド中央)

期待動作:
    - 3 チームが互いに戦い、障害物を迂回しながら移動する
    - ローカルミニマム（ポテンシャル合算ベクトルが 1e-6 以下）が頻発しない
    - BOOST_START / MELEE_COMBO / ATTACK_BLOCKED_LOS が適宜発生する
    - シミュレーションが 5000 ステップ以内にクラッシュせず完了する
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Obstacle, Vector3, Weapon


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_weapon(weapon_id: str, is_melee: bool = False) -> Weapon:
    if is_melee:
        return Weapon(
            id=weapon_id,
            name="Beam Saber",
            power=80,
            range=50.0,
            accuracy=90,
            type="PHYSICAL",
            weapon_type="MELEE",
            is_melee=True,
            optimal_range=30.0,
            decay_rate=0.0,
            max_ammo=None,
            en_cost=0,
        )
    return Weapon(
        id=weapon_id,
        name="Beam Rifle",
        power=30,
        range=700.0,
        accuracy=75,
        type="BEAM",
        weapon_type="RANGED",
        is_melee=False,
        optimal_range=400.0,
        decay_rate=0.05,
        max_ammo=20,
        en_cost=10,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    max_hp: int = 250,
    with_melee: bool = True,
    strategy_mode: str = "AGGRESSIVE",
) -> MobileSuit:
    weapons = [_make_weapon(f"rifle_{name}")]
    if with_melee:
        weapons.append(_make_weapon(f"saber_{name}", is_melee=True))
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=max_hp,
        armor=0,
        mobility=1.0,
        position=position,
        weapons=weapons,
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_speed=100.0,
        acceleration=40.0,
        deceleration=60.0,
        max_en=1000,
        en_recovery=40,
        sensor_range=2500.0,
        strategy_mode=strategy_mode,
        boost_speed_multiplier=2.0,
        boost_en_cost=5.0,
        boost_max_duration=3.0,
        boost_cooldown=5.0,
    )


def _make_obstacle(obs_id: str, x: float, z: float, radius: float) -> Obstacle:
    return Obstacle(
        obstacle_id=obs_id,
        position=Vector3(x=x, y=0, z=z),
        radius=radius,
        height=200.0,
    )


# ---------------------------------------------------------------------------
# シナリオ定義
# ---------------------------------------------------------------------------

SCENARIO_NAME = "scenario_full_field"
SCENARIO_DESCRIPTION = (
    "5 個以上の障害物フィールドで 3 チーム戦。"
    "全システム統合動作・ローカルミニマム発生頻度を確認する。"
)


def build_scenario() -> dict:
    """シナリオのユニット・障害物を構築して返す."""
    # チームA (PLAYER)
    unit_a = _make_unit(
        "TeamA_MS",
        "PLAYER",
        "TEAM_A",
        Vector3(x=500, y=0, z=2500),
        strategy_mode="ASSAULT",
    )
    # チームB (ENEMY)
    unit_b = _make_unit(
        "TeamB_MS",
        "ENEMY",
        "TEAM_B",
        Vector3(x=2500, y=0, z=500),
        strategy_mode="AGGRESSIVE",
    )
    # チームC (ENEMY)
    unit_c = _make_unit(
        "TeamC_MS",
        "ENEMY",
        "TEAM_C",
        Vector3(x=2500, y=0, z=4500),
        strategy_mode="AGGRESSIVE",
    )
    obstacles = [
        _make_obstacle("obs1", 1000.0, 1000.0, 150.0),
        _make_obstacle("obs2", 2000.0, 2000.0, 120.0),
        _make_obstacle("obs3", 3000.0, 1500.0, 100.0),
        _make_obstacle("obs4", 1500.0, 3500.0, 130.0),
        _make_obstacle("obs5", 3500.0, 3000.0, 110.0),
        _make_obstacle("obs6", 2500.0, 2500.0, 140.0),
    ]
    return {
        "name": SCENARIO_NAME,
        "description": SCENARIO_DESCRIPTION,
        "player": unit_a,
        "enemies": [unit_b, unit_c],
        "obstacles": obstacles,
    }


def run_scenario(max_steps: int = 5000) -> dict:
    """シナリオを実行して結果 dict を返す.

    チームAの遠距離武器弾薬を0に設定し、ENGAGE_MELEE→BOOST_DASHが
    発動しやすい状態にする。

    Returns:
        {
            "scenario": シナリオ名,
            "step_count": 実行ステップ数,
            "elapsed_time": 経過時間 (s),
            "win_loss": "WIN" / "LOSE" / "DRAW",
            "boost_start_count": BOOST_START ログ数,
            "melee_combo_count": MELEE_COMBO ログ数,
            "attack_blocked_los_count": ATTACK_BLOCKED_LOS ログ数,
            "log_action_types": 出力された action_type の種類セット,
            "logs": BattleLog リスト,
        }
    """
    data = build_scenario()
    sim = BattleSimulator(
        player=data["player"],
        enemies=data["enemies"],
        obstacles=data["obstacles"],
    )

    # チームAの遠距離武器弾薬を0に設定 (ENGAGE_MELEE を発動させる)
    player_id = str(data["player"].id)
    for weapon in data["player"].weapons:
        if not getattr(weapon, "is_melee", False):
            sim.unit_resources[player_id]["weapon_states"][weapon.id][
                "current_ammo"
            ] = 0

    step_count = 0
    for _ in range(max_steps):
        if sim.is_finished:
            break
        sim.step()
        step_count += 1

    alive_teams = {u.team_id for u in sim.units if u.current_hp > 0}
    player_team = data["player"].team_id
    if player_team in alive_teams and len(alive_teams) == 1:
        win_loss = "WIN"
    elif player_team not in alive_teams:
        win_loss = "LOSE"
    else:
        win_loss = "DRAW"

    action_types = {log.action_type for log in sim.logs}

    return {
        "scenario": SCENARIO_NAME,
        "step_count": step_count,
        "elapsed_time": sim.elapsed_time,
        "win_loss": win_loss,
        "boost_start_count": sum(
            1 for log in sim.logs if log.action_type == "BOOST_START"
        ),
        "melee_combo_count": sum(
            1 for log in sim.logs if log.action_type == "MELEE_COMBO"
        ),
        "attack_blocked_los_count": sum(
            1 for log in sim.logs if log.action_type == "ATTACK_BLOCKED_LOS"
        ),
        "log_action_types": action_types,
        "logs": sim.logs,
    }


if __name__ == "__main__":
    result = run_scenario()
    print(f"シナリオ: {result['scenario']}")
    print(f"ステップ数: {result['step_count']}, 経過時間: {result['elapsed_time']:.1f}s")
    print(f"結果: {result['win_loss']}")
    print(f"BOOST_START 回数: {result['boost_start_count']}")
    print(f"MELEE_COMBO 回数: {result['melee_combo_count']}")
    print(f"ATTACK_BLOCKED_LOS 回数: {result['attack_blocked_los_count']}")
    print(f"出力 action_type 種類: {sorted(result['log_action_types'])}")
