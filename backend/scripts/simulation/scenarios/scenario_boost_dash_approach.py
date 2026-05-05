#!/usr/bin/env python3
"""シナリオ: scenario_boost_dash_approach.

遠距離 (1200m) に配置された ASSAULT MS が障害物を迂回しながら
ブーストダッシュで格闘圏 (50m) まで接近する。

配置:
    Player  (0, 0, 0)      strategy_mode=ASSAULT, 格闘武器+遠距離武器
    Obstacle (600, 0, 150)  radius=80  (斜め配置で迂回を促す)
    Enemy   (1200, 0, 0)   strategy_mode=DEFENSIVE

期待動作:
    - Player が BOOST_START ログを出力してブーストダッシュを開始する
    - Player が格闘圏 (MELEE_RANGE=50m) まで接近する
    - ENGAGE_MELEE または BOOST_END ログが発生する
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.engine.simulation import BattleSimulator
from app.engine.constants import (
    DEFAULT_BOOST_COOLDOWN,
    DEFAULT_BOOST_EN_COST,
    DEFAULT_BOOST_MAX_DURATION,
    DEFAULT_BOOST_SPEED_MULTIPLIER,
)
from app.models.models import MobileSuit, Obstacle, Vector3, Weapon


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_melee_weapon() -> Weapon:
    return Weapon(
        id="beam_saber",
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


def _make_ranged_weapon(weapon_id: str = "beam_rifle", max_ammo: int | None = 20) -> Weapon:
    return Weapon(
        id=weapon_id,
        name="Beam Rifle",
        power=25,
        range=800.0,
        accuracy=75,
        type="BEAM",
        weapon_type="RANGED",
        is_melee=False,
        optimal_range=400.0,
        decay_rate=0.05,
        max_ammo=max_ammo,
        en_cost=10,
    )


def _make_assault_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    max_hp: int = 200,
) -> MobileSuit:
    """ASSAULT 戦略の高機動ユニットを生成する."""
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=max_hp,
        armor=0,
        mobility=1.2,
        position=position,
        weapons=[_make_melee_weapon(), _make_ranged_weapon(f"rifle_{name}")],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "MELEE"},
        max_speed=150.0,
        acceleration=60.0,
        deceleration=80.0,
        max_en=1000,
        en_recovery=30,
        sensor_range=3000.0,
        strategy_mode="ASSAULT",
        # ブーストパラメータ: 高機動型
        boost_speed_multiplier=DEFAULT_BOOST_SPEED_MULTIPLIER,
        boost_en_cost=DEFAULT_BOOST_EN_COST,
        boost_max_duration=DEFAULT_BOOST_MAX_DURATION,
        boost_cooldown=DEFAULT_BOOST_COOLDOWN,
    )


def _make_defensive_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    max_hp: int = 200,
) -> MobileSuit:
    """DEFENSIVE 戦略の防御ユニットを生成する."""
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=max_hp,
        armor=5,
        mobility=0.8,
        position=position,
        weapons=[_make_ranged_weapon(f"rifle_{name}")],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "RANGED"},
        max_speed=60.0,
        acceleration=20.0,
        deceleration=40.0,
        max_en=800,
        en_recovery=80,
        sensor_range=2500.0,
        strategy_mode="DEFENSIVE",
    )


# ---------------------------------------------------------------------------
# シナリオ定義
# ---------------------------------------------------------------------------

SCENARIO_NAME = "scenario_boost_dash_approach"
SCENARIO_DESCRIPTION = (
    "遠距離から ASSAULT MS が障害物を迂回しながらブーストダッシュで格闘圏に到達する。"
    "ブーストダッシュの距離詰め・キャンセル判定を検証する。"
)


def build_scenario() -> dict:
    """シナリオのユニット・障害物を構築して返す."""
    player = _make_assault_unit(
        "AssaultMS",
        "PLAYER",
        "PLAYER_TEAM",
        Vector3(x=0, y=0, z=0),
    )
    enemy = _make_defensive_unit(
        "DefenderMS",
        "ENEMY",
        "ENEMY_TEAM",
        Vector3(x=1200, y=0, z=0),
    )
    # 障害物: 斜め配置で迂回行動を促す
    obstacle = Obstacle(
        obstacle_id="obs_side",
        position=Vector3(x=600, y=0, z=150),
        radius=80.0,
        height=150.0,
    )
    return {
        "name": SCENARIO_NAME,
        "description": SCENARIO_DESCRIPTION,
        "player": player,
        "enemies": [enemy],
        "obstacles": [obstacle],
    }


def run_scenario(max_steps: int = 5000) -> dict:
    """シナリオを実行して結果 dict を返す.

    Player の遠距離武器弾薬を 0 に設定することで ENGAGE_MELEE を強制し、
    距離が MELEE_BOOST_ARRIVAL_RANGE(100m) 超のため BOOST_DASH が起動する。

    Returns:
        {
            "scenario": シナリオ名,
            "step_count": 実行ステップ数,
            "elapsed_time": 経過時間 (s),
            "win_loss": "WIN" / "LOSE" / "DRAW",
            "boost_start_count": BOOST_START ログ数,
            "boost_end_count": BOOST_END ログ数,
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

    # Player の遠距離武器弾薬を 0 に設定（ENGAGE_MELEE を強制）
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
    if data["player"].team_id in alive_teams and len(alive_teams) == 1:
        win_loss = "WIN"
    elif data["player"].team_id not in alive_teams:
        win_loss = "LOSE"
    else:
        win_loss = "DRAW"

    action_types = {log.action_type for log in sim.logs}
    boost_start_count = sum(1 for log in sim.logs if log.action_type == "BOOST_START")
    boost_end_count = sum(1 for log in sim.logs if log.action_type == "BOOST_END")

    return {
        "scenario": SCENARIO_NAME,
        "step_count": step_count,
        "elapsed_time": sim.elapsed_time,
        "win_loss": win_loss,
        "boost_start_count": boost_start_count,
        "boost_end_count": boost_end_count,
        "engage_melee_occurred": "ENGAGE_MELEE" in action_types
        or "MELEE_COMBO" in action_types,
        "log_action_types": action_types,
        "logs": sim.logs,
    }


if __name__ == "__main__":
    result = run_scenario()
    print(f"シナリオ: {result['scenario']}")
    print(f"ステップ数: {result['step_count']}, 経過時間: {result['elapsed_time']:.1f}s")
    print(f"結果: {result['win_loss']}")
    print(f"BOOST_START 回数: {result['boost_start_count']}")
    print(f"BOOST_END 回数: {result['boost_end_count']}")
    print(f"格闘突入発生: {result['engage_melee_occurred']}")
    print(f"出力 action_type 種類: {sorted(result['log_action_types'])}")
