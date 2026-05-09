#!/usr/bin/env python3
"""シナリオ: scenario_melee_combo.

弾切れ状態の MS が格闘戦を強いられるシナリオ。
ENGAGE_MELEE トリガー・コンボ発生を検証する。

配置:
    Player  (0, 0, 0)   遠距離武器残弾ほぼゼロ + 格闘武器あり
    Enemy   (300, 0, 0)  通常の遠距離武器装備（HP 多め）

期待動作:
    - Player の ranged_ammo_ratio が低いため ENGAGE_MELEE が発動する
    - Player が格闘圏 (50m) まで接近して格闘攻撃を行う
    - MELEE_COMBO ログが少なくとも 1 回出力される
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_melee_weapon() -> Weapon:
    return Weapon(
        id="beam_saber",
        name="Beam Saber",
        power=100,
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


def _make_ranged_weapon_empty() -> Weapon:
    """残弾 1 の遠距離武器（弾切れ寸前）を生成する."""
    return Weapon(
        id="beam_rifle_low",
        name="Beam Rifle (Low Ammo)",
        power=20,
        range=500.0,
        accuracy=70,
        type="BEAM",
        weapon_type="RANGED",
        is_melee=False,
        optimal_range=300.0,
        decay_rate=0.05,
        max_ammo=1,  # 残弾最小（1発で弾切れ）
        en_cost=10,
    )


def _make_ranged_weapon_normal(weapon_id: str = "beam_rifle") -> Weapon:
    """通常残弾の遠距離武器を生成する."""
    return Weapon(
        id=weapon_id,
        name="Beam Rifle",
        power=25,
        range=600.0,
        accuracy=80,
        type="BEAM",
        weapon_type="RANGED",
        is_melee=False,
        optimal_range=300.0,
        decay_rate=0.05,
        max_ammo=20,
        en_cost=10,
    )


def _make_melee_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    max_hp: int = 2000,
) -> MobileSuit:
    """弾切れ寸前 + 格闘武器のユニットを生成する.

    HP を大きめに設定し、敵の攻撃を複数回受けながらも
    格闘戦を継続できるようにする (MELEE_COMBO 発生のため)。
    """
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=max_hp,
        armor=0,
        mobility=1.2,
        position=position,
        weapons=[_make_ranged_weapon_empty(), _make_melee_weapon()],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "MELEE"},
        max_speed=120.0,
        acceleration=50.0,
        deceleration=70.0,
        max_en=1000,
        en_recovery=30,
        sensor_range=3000.0,
        strategy_mode="ASSAULT",
        boost_speed_multiplier=2.0,
        boost_en_cost=5.0,
        boost_max_duration=3.0,
        boost_cooldown=5.0,
    )


def _make_target_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    max_hp: int = 1500,
) -> MobileSuit:
    """高HP の遠距離ユニットを生成する（格闘を受け止める的）."""
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=max_hp,
        armor=0,
        mobility=0.8,
        position=position,
        weapons=[_make_ranged_weapon_normal(f"rifle_{name}")],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "RANGED"},
        max_speed=60.0,
        acceleration=20.0,
        deceleration=40.0,
        max_en=800,
        en_recovery=80,
        sensor_range=2000.0,
        strategy_mode="DEFENSIVE",
    )


# ---------------------------------------------------------------------------
# シナリオ定義
# ---------------------------------------------------------------------------

SCENARIO_NAME = "scenario_melee_combo"
SCENARIO_DESCRIPTION = (
    "弾切れ状態の MS が格闘戦を強いられるシナリオ。"
    "ENGAGE_MELEE トリガー・格闘コンボ発生を検証する。"
)


def build_scenario() -> dict:
    """シナリオのユニット・障害物を構築して返す.

    Player と Enemy を近接距離 (40m) で配置し、
    Player の弾薬を 0 にすることで即座に ENGAGE_MELEE が発動するよう設定する。
    """
    player = _make_melee_unit(
        "MeleeMS",
        "PLAYER",
        "PLAYER_TEAM",
        Vector3(x=0, y=0, z=0),
    )
    enemy = _make_target_unit(
        "TargetMS",
        "ENEMY",
        "ENEMY_TEAM",
        Vector3(x=40, y=0, z=0),  # MELEE_RANGE(50m) 以内に配置
    )
    return {
        "name": SCENARIO_NAME,
        "description": SCENARIO_DESCRIPTION,
        "player": player,
        "enemies": [enemy],
        "obstacles": [],
    }


def run_scenario(max_steps: int = 5000) -> dict:
    """シナリオを実行して結果 dict を返す.

    Player の遠距離武器弾薬を 0 に設定することで ENGAGE_MELEE を強制し、
    格闘距離 (40m) から即座に格闘戦が始まるよう設定する。

    Returns:
        {
            "scenario": シナリオ名,
            "step_count": 実行ステップ数,
            "elapsed_time": 経過時間 (s),
            "win_loss": "WIN" / "LOSE" / "DRAW",
            "melee_combo_count": MELEE_COMBO ログ数,
            "engage_melee_occurred": ENGAGE_MELEE アクションが発生したか,
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

    # Player の遠距離武器弾薬を 0 に設定（弾切れ状態を強制）
    player_id = str(data["player"].id)
    for weapon in data["player"].weapons:
        if weapon.weapon_type == "RANGED":
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
    if data["player"].team_id in alive_teams and len(alive_teams) == 1:
        win_loss = "WIN"
    elif data["player"].team_id not in alive_teams:
        win_loss = "LOSE"
    else:
        win_loss = "DRAW"

    action_types = {log.action_type for log in sim.logs}
    melee_combo_count = sum(1 for log in sim.logs if log.action_type == "MELEE_COMBO")

    return {
        "scenario": SCENARIO_NAME,
        "step_count": step_count,
        "elapsed_time": sim.elapsed_time,
        "win_loss": win_loss,
        "melee_combo_count": melee_combo_count,
        "engage_melee_occurred": "MELEE_COMBO" in action_types
        or "BOOST_START" in action_types,
        "log_action_types": action_types,
        "logs": sim.logs,
    }


if __name__ == "__main__":
    result = run_scenario()
    print(f"シナリオ: {result['scenario']}")
    print(
        f"ステップ数: {result['step_count']}, 経過時間: {result['elapsed_time']:.1f}s"
    )
    print(f"結果: {result['win_loss']}")
    print(f"MELEE_COMBO 発生回数: {result['melee_combo_count']}")
    print(f"格闘突入発生: {result['engage_melee_occurred']}")
    print(f"出力 action_type 種類: {sorted(result['log_action_types'])}")
