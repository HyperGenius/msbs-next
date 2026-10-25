# backend/app/services/mission_battle.py
"""作戦マスターから、作戦の戦闘に渡す機体・配置・目標を組み立てる.

どの関数も DB セッションを使わない。
"""

import copy
import uuid
from dataclasses import dataclass, field, replace
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
from app.engine.suppression import SuppressionConfig
from app.engine.unit_roles import UnitAssignment
from app.models.models import (
    ALL_PART_NAMES,
    MISSION_TEAM_ENEMY,
    MISSION_TEAM_PLAYER,
    MISSION_UNIT_DEFAULT_NAME,
    MasterMobileSuit,
    Mission,
    MissionUnitConfig,
    MobileSuit,
    RetreatPoint,
    SpawnZone,
    Weapon,
)
from app.services.matching_service import MatchingService
from app.services.mobile_suit_service import master_mobile_suit_fields
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
    suppression: SuppressionConfig
    """射撃の制圧。作戦の戦闘でだけ有効にする。"""


@dataclass(frozen=True)
class MissionMasters:
    """作戦の機体が参照する機体マスターとエース.

    呼び出し側が DB かロスターから読んで渡す。
    """

    mobile_suits: dict[str, MasterMobileSuit] = field(default_factory=dict)
    """機体マスター ID → 機体マスター。武器の `master_weapon_id` は書き込み済みであること。"""
    aces: dict[str, dict[str, Any]] = field(default_factory=dict)
    """エース ID → `get_ace_pilots()` が返す形のエースのマスター。"""


def referenced_master_ids(mission: Mission) -> tuple[list[str], list[str]]:
    """作戦の機体が参照する機体マスター ID とエース ID を、出てくる順に重複なく返す."""
    configs = [*mission.ally_unit_configs(), *mission.enemy_unit_configs()]
    mobile_suit_ids = [
        c.master_mobile_suit_id for c in configs if c.master_mobile_suit_id is not None
    ]
    ace_ids = [c.ace_id for c in configs if c.ace_id is not None]
    return list(dict.fromkeys(mobile_suit_ids)), list(dict.fromkeys(ace_ids))


def build_mission_unit(
    config: MissionUnitConfig,
    side: str,
    unit_id: uuid.UUID | None = None,
    masters: MissionMasters | None = None,
) -> MobileSuit:
    """作戦マスターの1機の定義から機体を作る. `unit_id` を省くと ID はランダムにする.

    Raises:
        ValueError: 無い部位を書いたとき。参照先のマスターが `masters` に無いとき。
            エースを敵機以外に置いたとき。
    """
    unknown_parts = set(config.missing_parts) - set(ALL_PART_NAMES)
    if unknown_parts:
        raise ValueError(f"unknown parts: {sorted(unknown_parts)}")
    if config.ace_id is not None and side != "ENEMY":
        raise ValueError(f"ace must be an enemy: {config.ace_id}")
    unit = (
        _build_referenced_unit(config, masters or MissionMasters())
        if config.references_master
        else _build_inline_unit(config)
    )
    unit.id = unit_id or uuid.uuid4()
    unit.side = side
    unit.position = config.position.model_copy()
    if config.name is not None:
        unit.name = config.name
    unit.missing_parts = list(
        dict.fromkeys([*unit.missing_parts, *config.missing_parts])
    )
    if config.current_hp_ratio is not None:
        unit.current_hp = max(1, round(unit.max_hp * config.current_hp_ratio))
    elif config.current_hp is not None:
        unit.current_hp = min(config.current_hp, unit.max_hp)
    if config.max_speed is not None:
        unit.max_speed = config.max_speed
    if config.role in (UNIT_ROLE_SUPPORT, UNIT_ROLE_SNIPER):
        unit.tactics = {**unit.tactics, "priority": TACTICS_PRIORITY_SUPPORT}
    unit.normalize_parts()
    if unit.current_hp < unit.max_hp:
        _scale_part_hp(unit)
    return unit


def _build_inline_unit(config: MissionUnitConfig) -> MobileSuit:
    """作戦マスターに直書きした性能と武器から機体を作る."""
    return MobileSuit(
        name=MISSION_UNIT_DEFAULT_NAME,
        max_hp=config.max_hp,
        current_hp=config.max_hp,
        armor=config.armor,
        mobility=config.mobility,
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
    )


def _build_referenced_unit(
    config: MissionUnitConfig, masters: MissionMasters
) -> MobileSuit:
    """機体マスターかエースから機体を作る.

    エースに機体マスターを重ねたときは、性能・武器・地形適性だけを機体マスターにする。
    パイロット・性格・戦術・懸賞金はエースのまま残す。
    """
    master: MasterMobileSuit | None = None
    if config.master_mobile_suit_id is not None:
        master = masters.mobile_suits.get(config.master_mobile_suit_id)
        if master is None:
            raise ValueError(
                f"unknown master mobile suit: {config.master_mobile_suit_id}"
            )
    if config.ace_id is None:
        assert master is not None
        unit = MobileSuit(name=master.name, **master_mobile_suit_fields(master))
    else:
        ace = masters.aces.get(config.ace_id)
        if ace is None:
            raise ValueError(f"unknown ace: {config.ace_id}")
        # build_ace_mobile_suit() は武器と戦術をそのまま機体に渡す。
        # マスターは戦闘をまたいで使い回すため、機体と共有しない。
        unit = MatchingService.build_ace_mobile_suit(
            copy.deepcopy(ace), position=config.position.model_copy()
        )
        if master is not None:
            for key, value in master_mobile_suit_fields(master).items():
                setattr(unit, key, value)
            unit.name = master.name
    if master is not None:
        unit.terrain_adaptability = dict(master.specs.get("terrain_adaptability") or {})
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
    masters: MissionMasters | None = None,
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
        masters: 作戦の機体が参照する機体マスターとエース。

    Raises:
        ValueError: 作戦目標の種類やロールが無いとき。参照先のマスターが無いとき。
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
            unit = build_mission_unit(config, side, unit_id, masters)
            unit.team_id = team_ids[team_key]
            mission_units.append(unit)
            if (
                config.role is not None
                or config.squad_id is not None
                or config.hold_fire
            ):
                unit_assignments[str(unit.id)] = UnitAssignment(
                    role=config.role,
                    squad_id=config.squad_id,
                    hold_fire=config.hold_fire,
                )

    if conditions.theater_id is None:
        conditions = replace(conditions, environment=mission.environment)

    layout = mission.layout_config()
    # エリア収縮はバトルロイヤルで接敵させる仕組みなので、作戦では使わない。
    battlefield_update: dict = {"area_shrink": False, "field_size": layout.field_size}
    if layout.spawn_zones:
        battlefield_update["spawn_zones"] = [
            SpawnZone(
                team_id=team_ids[zone.team_id],
                center=zone.center.model_copy(),
                radius=zone.radius,
            )
            for zone in layout.spawn_zones
        ]
    conditions = replace(
        conditions,
        battlefield=conditions.battlefield.model_copy(update=battlefield_update),
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
        suppression=SuppressionConfig(),
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
