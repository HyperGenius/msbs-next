#!/usr/bin/env python3
"""シナリオ: scenario_los_obstacle_basic.

障害物 1 個の単純フィールドで 2 機対戦。
LOS 遮断・索敵ブロック・迂回行動を検証する。

配置:
    Player  (0, 0, 0)
    Obstacle (500, 0, 0)  radius=100
    Enemy   (1000, 0, 0)

期待動作:
    - 初期状態で Obstacle が LOS を遮断する
    - Player は ATTACK_BLOCKED_LOS ログを出力するか、迂回経路を進む
    - 最終的に Player が Enemy を視認して攻撃できる
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Obstacle, Vector3, Weapon

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_ranged_weapon(weapon_id: str = "beam_rifle") -> Weapon:
    return Weapon(
        id=weapon_id,
        name="Beam Rifle",
        power=30,
        range=800.0,
        accuracy=80,
        type="BEAM",
        weapon_type="RANGED",
        is_melee=False,
        optimal_range=400.0,
        decay_rate=0.05,
        max_ammo=30,
        en_cost=10,
    )


def _make_unit(
    name: str,
    side: str,
    team_id: str,
    position: Vector3,
    max_hp: int = 200,
    sensor_range: float = 2000.0,
    strategy_mode: str | None = "AGGRESSIVE",
) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=max_hp,
        current_hp=max_hp,
        armor=0,
        mobility=1.0,
        position=position,
        weapons=[_make_ranged_weapon(f"weapon_{name}")],
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        max_speed=80.0,
        acceleration=30.0,
        deceleration=50.0,
        max_en=1000,
        en_recovery=50,
        sensor_range=sensor_range,
        strategy_mode=strategy_mode,
    )


# ---------------------------------------------------------------------------
# シナリオ定義
# ---------------------------------------------------------------------------

SCENARIO_NAME = "scenario_los_obstacle_basic"
SCENARIO_DESCRIPTION = (
    "障害物 1 個の単純フィールドで 2 機対戦。"
    "LOS 遮断・索敵ブロック・障害物迂回行動を検証する。"
)


def build_scenario() -> dict:
    """シナリオのユニット・障害物を構築して返す."""
    player = _make_unit(
        "PlayerMS",
        "PLAYER",
        "PLAYER_TEAM",
        Vector3(x=0, y=0, z=0),
    )
    enemy = _make_unit(
        "EnemyMS",
        "ENEMY",
        "ENEMY_TEAM",
        Vector3(x=1000, y=0, z=0),
    )
    # 障害物: Player と Enemy の間に配置（LOS を遮断）
    obstacle = Obstacle(
        obstacle_id="obs_center",
        position=Vector3(x=500, y=0, z=0),
        radius=100.0,
        height=200.0,
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

    Args:
        max_steps: 最大ステップ数

    Returns:
        {
            "scenario": シナリオ名,
            "step_count": 実行ステップ数,
            "elapsed_time": 経過時間 (s),
            "win_loss": "WIN" / "LOSE" / "DRAW",
            "log_action_types": 出力された action_type の種類セット,
            "attack_blocked_los_count": ATTACK_BLOCKED_LOS ログ数,
            "logs": BattleLog リスト（dict 化）,
        }
    """
    data = build_scenario()
    sim = BattleSimulator(
        player=data["player"],
        enemies=data["enemies"],
        obstacles=data["obstacles"],
    )

    step_count = 0
    for _ in range(max_steps):
        if sim.is_finished:
            break
        sim.step()
        step_count += 1

    player_team = data["player"].team_id
    alive_teams = {u.team_id for u in sim.units if u.current_hp > 0}
    if player_team in alive_teams and len(alive_teams) == 1:
        win_loss = "WIN"
    elif player_team not in alive_teams:
        win_loss = "LOSE"
    else:
        win_loss = "DRAW"

    action_types = {log.action_type for log in sim.logs}
    attack_blocked_count = sum(
        1 for log in sim.logs if log.action_type == "ATTACK_BLOCKED_LOS"
    )

    return {
        "scenario": SCENARIO_NAME,
        "step_count": step_count,
        "elapsed_time": sim.elapsed_time,
        "win_loss": win_loss,
        "log_action_types": action_types,
        "attack_blocked_los_count": attack_blocked_count,
        "logs": sim.logs,
    }


if __name__ == "__main__":
    result = run_scenario()
    print(f"シナリオ: {result['scenario']}")
    print(
        f"ステップ数: {result['step_count']}, 経過時間: {result['elapsed_time']:.1f}s"
    )
    print(f"結果: {result['win_loss']}")
    print(f"ATTACK_BLOCKED_LOS 回数: {result['attack_blocked_los_count']}")
    print(f"出力 action_type 種類: {sorted(result['log_action_types'])}")
