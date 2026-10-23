# backend/app/engine/formation.py
"""小隊の陣形. 後衛（支援・狙撃）を同じ小隊の前衛の後方に位置取らせる."""

import math
from typing import TYPE_CHECKING, NamedTuple

import numpy as np

from app.engine.constants import (
    BOUNDARY_MARGIN,
    FORMATION_ANCHOR_SLACK,
    FORMATION_ATTRACTION_COEFF,
    FORMATION_MIN_GAP,
    FORMATION_REAR_ROLES,
    FORMATION_VANGUARD_CONTACT_RANGE,
    OBSTACLE_MARGIN,
    UNIT_ROLE_VANGUARD,
)
from app.engine.spatial_grid import UnitSpatialGrid
from app.models.models import MobileSuit, Obstacle

if TYPE_CHECKING:
    from app.engine.movement import EngagementRange

SquadKey = tuple[str | None, str]


class FormationAnchor(NamedTuple):
    """後衛が目指す位置と、その基準にした敵の位置."""

    position: np.ndarray
    enemy_position: np.ndarray | None


class FormationMixin:
    """小隊の陣形の力を計算するミックスイン."""

    # BattleSimulator が提供するインスタンス属性 (mypy 向け型宣言のみ; 実体は simulation.py)
    units: list[MobileSuit]
    unit_resources: dict[str, dict]
    team_detected_units: dict[str, set]
    obstacles: list[Obstacle]
    map_bounds: tuple[float, float]
    _squad_vanguards: dict[SquadKey, list[MobileSuit]] | None

    def _resolve_squad_vanguards(self) -> dict[SquadKey, list[MobileSuit]]:
        """小隊ごとの戦闘中の前衛を返す.

        1 ステップに 1 回だけ解決する。`step()` の冒頭でキャッシュを破棄する。
        """
        if self._squad_vanguards is None:
            vanguards: dict[SquadKey, list[MobileSuit]] = {}
            for unit in self.units:
                squad_id = self.squad_id(unit)  # type: ignore[attr-defined]
                if (
                    squad_id is None
                    or self.unit_role(unit) != UNIT_ROLE_VANGUARD  # type: ignore[attr-defined]
                    or not self._is_in_combat(unit)
                ):
                    continue
                vanguards.setdefault((unit.team_id, squad_id), []).append(unit)
            self._squad_vanguards = vanguards
        return self._squad_vanguards

    def _is_in_combat(self, unit: MobileSuit) -> bool:
        """撃破も撤退もしていないか."""
        return (
            unit.current_hp > 0
            and self.unit_resources[str(unit.id)].get("status") == "ACTIVE"
        )

    def _formation_force(
        self,
        unit: MobileSuit,
        pos_unit: np.ndarray,
        engagement: "EngagementRange | None",
        current_action: str,
    ) -> np.ndarray:
        """後衛を、同じ小隊の前衛の後方へ引き寄せる力を返す.

        小隊の前衛がいないとき・逃走中・敵に詰められたときは 0 を返す。
        詰められたときは、間合いのばねによる後退を優先させるため。
        """
        squad_id = self.squad_id(unit)  # type: ignore[attr-defined]
        if (
            squad_id is None
            or self.unit_role(unit) not in FORMATION_REAR_ROLES  # type: ignore[attr-defined]
            or engagement is None
            or current_action not in ("ATTACK", "MOVE")
            or self.unit_resources[str(unit.id)].get("fleeing", False)
        ):
            return np.zeros(3)
        vanguards = [
            v
            for v in self._resolve_squad_vanguards().get((unit.team_id, squad_id), [])
            if self._is_in_combat(v)
        ]
        if not vanguards:
            return np.zeros(3)

        grid = self._get_movement_grid()  # type: ignore[attr-defined]
        threat = self._nearest_detected_enemy(grid, unit.team_id, pos_unit)
        if (
            threat is not None
            and _xz_distance(pos_unit, threat.position.to_numpy())
            < engagement.distance - engagement.tolerance
        ):
            return np.zeros(3)

        vanguard = min(
            vanguards,
            key=lambda v: _xz_distance(pos_unit, v.position.to_numpy()),
        )
        anchor = self._formation_anchor(grid, vanguard, engagement.distance)
        if anchor is None:
            return np.zeros(3)
        vec = anchor.position - pos_unit
        vec[1] = 0.0
        dist = float(np.linalg.norm(vec))
        if dist < 1e-6:
            return np.zeros(3)
        ratio = min(1.0, dist / FORMATION_ANCHOR_SLACK)
        force = FORMATION_ATTRACTION_COEFF * ratio * vec / dist
        if anchor.enemy_position is not None:
            force = _without_inward_component(
                force, pos_unit, anchor.enemy_position, anchor.position
            )
        return force

    def _formation_anchor(
        self,
        grid: UnitSpatialGrid,
        vanguard: MobileSuit,
        engagement_distance: float,
    ) -> FormationAnchor | None:
        """後衛が目指す位置を返す.

        前衛に最も近い索敵済みの敵から見て、前衛の向こう側に置く。
        敵からの距離は後衛の目標交戦距離にし、前衛との間は `FORMATION_MIN_GAP` 以上あける。
        索敵済みの敵がいなければ、前衛の胴体の向きの後方に置く。
        前衛が敵と `FORMATION_VANGUARD_CONTACT_RANGE` 未満にいれば None を返す。
        """
        pos_vanguard = vanguard.position.to_numpy()
        enemy = self._nearest_detected_enemy(grid, vanguard.team_id, pos_vanguard)
        if enemy is None:
            heading = math.radians(
                self.unit_resources[str(vanguard.id)].get("body_heading_deg", 0.0)
            )
            forward = np.array([math.cos(heading), 0.0, math.sin(heading)])
            anchor = pos_vanguard - forward * FORMATION_MIN_GAP
            return FormationAnchor(self._keep_anchor_in_field(anchor), None)

        pos_enemy = enemy.position.to_numpy()
        away = pos_vanguard - pos_enemy
        away[1] = 0.0
        dist = float(np.linalg.norm(away))
        if dist < FORMATION_VANGUARD_CONTACT_RANGE:
            return None
        anchor = pos_enemy + away / dist * max(
            dist + FORMATION_MIN_GAP, engagement_distance
        )
        anchor[1] = pos_vanguard[1]
        return FormationAnchor(self._keep_anchor_in_field(anchor), pos_enemy)

    def _nearest_detected_enemy(
        self, grid: UnitSpatialGrid, team_id: str | None, pos: np.ndarray
    ) -> MobileSuit | None:
        """`team_id` のチームが索敵済みの敵のうち、`pos` に最も近いものを返す."""
        detected = self.team_detected_units.get(team_id, set())  # type: ignore[arg-type]
        if not detected:
            return None
        return grid.nearest(
            pos,
            lambda u: u.current_hp > 0 and u.team_id != team_id and u.id in detected,
        )

    def _keep_anchor_in_field(self, anchor: np.ndarray) -> np.ndarray:
        """陣形の位置を、障害物の外とマップ境界の内側に移す.

        `map_bounds` は収縮後の境界なので、収縮エリアの内側にも収まる。
        障害物から押し出した後に境界で戻すので、境界際では障害物に掛かることがある。
        """
        anchor = anchor.copy()
        for obs in self.obstacles:
            center = obs.position.to_numpy()
            away = anchor - center
            away[1] = 0.0
            dist = float(np.linalg.norm(away))
            clearance = obs.radius + OBSTACLE_MARGIN
            if dist >= clearance:
                continue
            direction = away / dist if dist > 1e-6 else np.array([1.0, 0.0, 0.0])
            anchor[0] = center[0] + direction[0] * clearance
            anchor[2] = center[2] + direction[2] * clearance
        map_min, map_max = self.map_bounds
        low, high = map_min + BOUNDARY_MARGIN, map_max - BOUNDARY_MARGIN
        if low > high:
            low = high = (map_min + map_max) / 2.0
        anchor[0] = min(max(anchor[0], low), high)
        anchor[2] = min(max(anchor[2], low), high)
        return anchor


def _without_inward_component(
    force: np.ndarray,
    pos_unit: np.ndarray,
    pos_enemy: np.ndarray,
    anchor: np.ndarray,
) -> np.ndarray:
    """陣形の位置より敵に近いとき、敵へ向かう力の成分を消して返す.

    陣形の位置へ一直線に向かうと、敵の近くを横切る。
    敵から一定の距離を保ったまま、敵の周りを回って陣形の位置へ移らせる。
    """
    inward = pos_enemy - pos_unit
    inward[1] = 0.0
    dist = float(np.linalg.norm(inward))
    if dist < 1e-6 or dist >= _xz_distance(anchor, pos_enemy):
        return force
    inward /= dist
    toward = float(np.dot(force, inward))
    if toward <= 0.0:
        return force
    return force - toward * inward


def _xz_distance(a: np.ndarray, b: np.ndarray) -> float:
    return math.hypot(float(a[0] - b[0]), float(a[2] - b[2]))
