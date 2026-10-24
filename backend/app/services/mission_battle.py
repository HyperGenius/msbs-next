# backend/app/services/mission_battle.py
"""作戦マスターから、作戦の戦闘に渡す機体・配置・目標を組み立てる.

どの関数も DB セッションを使わない。
"""

import uuid
from dataclasses import dataclass, replace
from typing import Any

from app.engine.constants import (
    TACTICS_PRIORITY_SUPPORT,
    UNIT_ROLE_SNIPER,
    UNIT_ROLE_SUPPORT,
)
from app.engine.objectives import (
    BattleObjective,
    ObjectiveResult,
    ObjectiveStatus,
    build_objective,
)
from app.engine.simulation import BattleSimulator
from app.engine.unit_roles import UnitAssignment
from app.models.models import (
    ALL_PART_NAMES,
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


def build_mission_unit(
    config: MissionUnitConfig, side: str, unit_id: uuid.UUID | None = None
) -> MobileSuit:
    """作戦マスターの1機の定義から機体を作る. `unit_id` を省くと ID はランダムにする."""
    unknown_parts = set(config.missing_parts) - set(ALL_PART_NAMES)
    if unknown_parts:
        raise ValueError(f"unknown parts: {sorted(unknown_parts)}")
    unit = MobileSuit(
        id=unit_id or uuid.uuid4(),
        name=config.name,
        max_hp=config.max_hp,
        current_hp=(
            config.max_hp
            if config.current_hp is None
            else min(config.current_hp, config.max_hp)
        ),
        missing_parts=list(config.missing_parts),
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
                weapon_type=config.weapon.weapon_type,
                is_melee=config.weapon.is_melee,
                fire_arc_deg=config.weapon.fire_arc_deg,
            )
        ],
        side=side,
    )
    if config.role in (UNIT_ROLE_SUPPORT, UNIT_ROLE_SNIPER):
        unit.tactics = {**unit.tactics, "priority": TACTICS_PRIORITY_SUPPORT}
    unit.normalize_parts()
    if unit.current_hp < unit.max_hp:
        _scale_part_hp(unit)
    return unit


def _scale_part_hp(unit: MobileSuit) -> None:
    """機体の HP の割合に合わせて、各部位の HP を減らす."""
    ratio = max(unit.current_hp, 1) / unit.max_hp
    for part in unit.parts.values():
        part.current_hp = max(1, round(part.max_hp * ratio))


def enemy_team_id(mission: Mission) -> str:
    """作戦の敵機のチーム ID を返す。敵機は全員で1チームになる."""
    return f"mission-{mission.id}-enemy"


def build_mission_battle(
    mission: Mission,
    player_units: list[MobileSuit],
    conditions: BattleConditions,
    unit_id_namespace: uuid.UUID | None = None,
) -> MissionBattleSetup:
    """作戦マスターから戦闘に渡すものを組み立てる.

    プレイヤー機と友軍は先頭のプレイヤー機のチームに入れる。
    `player_units` の `team_id` は書き換える。

    Args:
        mission: 作戦マスター。
        player_units: 出撃するプレイヤー機。先頭の `team_id` が設定済みであること。
        conditions: その日の戦域の条件。戦域が無いときは作戦の環境を使う。
        unit_id_namespace: 指定すると、友軍・敵機の ID を作戦マスターでの位置から決める。
            ローカルシミュレータで、戦闘をまたいで同じ機体として数えるために使う。
            省くと ID はランダムにする。

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
        for index, config in enumerate(configs):
            unit_id = (
                uuid.uuid5(unit_id_namespace, f"{team_key}-{index}")
                if unit_id_namespace is not None
                else None
            )
            unit = build_mission_unit(config, side, unit_id)
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
    ally_ids = [str(u.id) for u in mission_units if u.team_id == player_team_id]
    return MissionBattleSetup(
        mission_units=mission_units,
        conditions=conditions,
        retreat_points=retreat_points,
        unit_assignments=unit_assignments,
        objective=build_objective(
            objective_config.type, objective_config.params, ally_ids
        ),
    )


WIN_LOSS_BY_OBJECTIVE_STATUS = {
    ObjectiveStatus.SUCCESS: "WIN",
    ObjectiveStatus.FAILURE: "LOSE",
    ObjectiveStatus.DRAW: "DRAW",
}
"""作戦の結果から `BattleResult.win_loss` への対応."""


def objective_result_fields(
    result: ObjectiveResult, simulator: BattleSimulator | None = None
) -> dict[str, Any]:
    """`BattleResult` の作戦の結果のカラムを組み立てる.

    `simulator` を渡すと、BattleViewer が撤退ポイントとロールを描くための
    `retreat_points` / `unit_roles` を `objective_detail` に含める。
    """
    detail: dict[str, Any] | None = None
    if result.total > 0:
        detail = {
            "total": result.total,
            "lost": result.lost,
            "player_survived": result.player_survived,
        }
    if simulator is not None and (
        simulator.retreat_points or simulator.unit_assignments
    ):
        detail = detail or {}
        detail["retreat_points"] = [
            {
                "position": rp.position.model_dump(),
                "radius": rp.radius,
                "team_id": rp.team_id,
            }
            for rp in simulator.retreat_points
        ]
        detail["unit_roles"] = {
            unit_id: assignment.role
            for unit_id, assignment in simulator.unit_assignments.items()
            if assignment.role is not None
        }
    return {
        "objective_status": result.status.value,
        "objective_progress": result.progress,
        "objective_required": result.required,
        "objective_detail": detail,
    }
