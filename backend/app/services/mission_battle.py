# backend/app/services/mission_battle.py
"""作戦マスターから、作戦の戦闘に渡す機体・配置・目標を組み立てる.

どの関数も DB セッションを使わない。
"""

from dataclasses import dataclass, replace

from app.engine.objectives import BattleObjective, build_objective
from app.engine.unit_roles import UnitAssignment
from app.models.models import (
    MISSION_TEAM_ENEMY,
    MISSION_TEAM_PLAYER,
    Mission,
    MissionUnitConfig,
    MobileSuit,
    RetreatPoint,
    SpawnZone,
    Weapon,
)
from app.services.theater_service import BattleConditions


@dataclass
class MissionBattleSetup:
    """作戦の戦闘に渡すもの."""

    mission_units: list[MobileSuit]
    """作戦マスターの友軍と敵機。プレイヤー機は含まない。"""
    conditions: BattleConditions
    retreat_points: list[RetreatPoint]
    unit_assignments: dict[str, UnitAssignment]
    objective: BattleObjective


def build_mission_unit(config: MissionUnitConfig, side: str) -> MobileSuit:
    """作戦マスターの1機の定義から機体を作る."""
    unit = MobileSuit(
        name=config.name,
        max_hp=config.max_hp,
        current_hp=config.max_hp,
        armor=config.armor,
        mobility=config.mobility,
        position=config.position.model_copy(),
        terrain_adaptability=dict(config.terrain_adaptability),
        weapons=[
            Weapon(
                id=config.weapon.id,
                name=config.weapon.name,
                power=config.weapon.power,
                range=config.weapon.range,
                accuracy=config.weapon.accuracy,
            )
        ],
        side=side,
    )
    unit.normalize_parts()
    return unit


def enemy_team_id(mission: Mission) -> str:
    """作戦の敵機のチーム ID を返す。敵機は全員で1チームになる."""
    return f"mission-{mission.id}-enemy"


def build_mission_battle(
    mission: Mission, player_units: list[MobileSuit], conditions: BattleConditions
) -> MissionBattleSetup:
    """作戦マスターから戦闘に渡すものを組み立てる.

    プレイヤー機と友軍は先頭のプレイヤー機のチームに入れる。
    `player_units` の `team_id` は書き換える。

    Args:
        mission: 作戦マスター。
        player_units: 出撃するプレイヤー機。先頭の `team_id` が設定済みであること。
        conditions: その日の戦域の条件。戦域が無いときは作戦の環境を使う。

    Raises:
        ValueError: 作戦目標の種類やロールが無いとき。
    """
    player_team_id = player_units[0].team_id
    if player_team_id is None:
        raise ValueError("player unit has no team_id")
    team_ids = {
        MISSION_TEAM_PLAYER: player_team_id,
        MISSION_TEAM_ENEMY: enemy_team_id(mission),
    }
    for unit in player_units:
        unit.team_id = player_team_id

    mission_units: list[MobileSuit] = []
    unit_assignments: dict[str, UnitAssignment] = {}
    for configs, side, team_key in (
        (mission.ally_unit_configs(), "PLAYER", MISSION_TEAM_PLAYER),
        (mission.enemy_unit_configs(), "ENEMY", MISSION_TEAM_ENEMY),
    ):
        for config in configs:
            unit = build_mission_unit(config, side)
            unit.team_id = team_ids[team_key]
            mission_units.append(unit)
            if config.role is not None or config.squad_id is not None:
                unit_assignments[str(unit.id)] = UnitAssignment(
                    role=config.role, squad_id=config.squad_id
                )

    if conditions.theater_id is None:
        conditions = replace(conditions, environment=mission.environment)

    layout = mission.layout_config()
    if layout.spawn_zones:
        conditions = replace(
            conditions,
            battlefield=conditions.battlefield.model_copy(
                update={
                    "spawn_zones": [
                        SpawnZone(
                            team_id=team_ids[zone.team_id],
                            center=zone.center.model_copy(),
                            radius=zone.radius,
                        )
                        for zone in layout.spawn_zones
                    ]
                }
            ),
        )
    retreat_points = [
        RetreatPoint(
            position=point.position.model_copy(),
            radius=point.radius,
            team_id=None if point.team_id is None else team_ids[point.team_id],
        )
        for point in layout.retreat_points
    ]

    objective_config = mission.objective_config()
    return MissionBattleSetup(
        mission_units=mission_units,
        conditions=conditions,
        retreat_points=retreat_points,
        unit_assignments=unit_assignments,
        objective=build_objective(objective_config.type, objective_config.params),
    )
