"""本番DBから参加機体と戦域条件を読み、ロスターを作る.

このモジュールは `app` を import する。本番DBに接続するときは、
import する前に `readonly_db.use_readonly_database()` を呼ぶこと。
"""

import random
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.core.gamedata import get_ace_pilots
from app.models.models import (
    AcePilot,
    MasterEnvironment,
    MasterTheater,
    MobileSuit,
    Pilot,
)
from app.services.matching_service import (
    MatchingService,
    build_npc_entry_snapshot,
    reset_npc_for_battle,
)
from app.services.mobile_suit_service import MobileSuitService
from app.services.pilot_service import PilotService
from app.services.theater_service import BattleConditions, TheaterService
from app.services.weapon_service import WeaponService
from scripts.simulation.local_sim.roster import (
    Roster,
    RosterConditions,
    RosterEntry,
    RosterEnvironmentProfile,
    RosterSource,
    RosterSourceKind,
    validate_roster_name,
)

MIN_ROSTER_ENTRIES = 2


@dataclass(frozen=True)
class UnitSpec:
    """`<ID>[:<チーム>]` 形式で指定した参加機体."""

    id: str
    team: str | None = None


def parse_unit_spec(value: str) -> UnitSpec:
    """`<ID>[:<チーム>]` を分解する.

    Raises:
        ValueError: ID またはチームが空の場合
    """
    unit_id, sep, team = value.partition(":")
    if not unit_id or (sep and not team):
        raise ValueError(f"'{value}' は <ID>[:<チーム>] の形式で指定してください。")
    return UnitSpec(id=unit_id, team=team or None)


@dataclass
class FetchOptions:
    """ロスターに入れる機体と戦域条件の指定."""

    mobile_suits: list[UnitSpec] = field(default_factory=list)
    pilots: list[UnitSpec] = field(default_factory=list)
    npc_count: int = 0
    ace_count: int = 0
    theater_id: str | None = None
    # None なら戦域の基準濃度。戦域も無ければ 0。
    minovsky_density: float | None = None


def resolve_conditions(
    session: Session, theater_id: str | None, minovsky_density: float | None
) -> RosterConditions:
    """戦域と濃度から、ロスターに保存する戦域条件を作る.

    Raises:
        ValueError: 戦域、または戦域の環境タイプがマスターに無い場合
    """
    if minovsky_density is not None and not 0.0 <= minovsky_density <= 1.0:
        raise ValueError("ミノフスキー濃度は 0〜1 で指定してください。")
    theater: MasterTheater | None = None
    if theater_id is None:
        conditions = BattleConditions(minovsky_density=minovsky_density or 0.0)
    else:
        theater = session.get(MasterTheater, theater_id)
        if theater is None:
            raise ValueError(f"戦域 '{theater_id}' がマスターにありません。")
        density = (
            minovsky_density if minovsky_density is not None else theater.base_minovsky
        )
        conditions = TheaterService.battle_conditions(session, theater_id, density)
        # battle_conditions() はマスターが欠けると既定の条件に落とす。黙って宇宙で戦わないように止める。
        if conditions.theater_id is None:
            raise ValueError(
                f"戦域 '{theater_id}' の環境タイプ '{theater.environment_id}' がマスターにありません。"
            )
    environment = session.get(MasterEnvironment, conditions.environment)
    return conditions_to_roster(
        conditions,
        theater_name=theater.name if theater else None,
        environment_name=environment.name if environment else None,
        viewer_preset=environment.viewer_preset if environment else None,
    )


def conditions_to_roster(
    conditions: BattleConditions,
    theater_name: str | None = None,
    environment_name: str | None = None,
    viewer_preset: str | None = None,
) -> RosterConditions:
    """`BattleConditions` を JSON に保存できる形にする."""
    profile = conditions.environment_profile
    return RosterConditions(
        theater_id=conditions.theater_id,
        environment=conditions.environment,
        environment_profile=(
            RosterEnvironmentProfile(**asdict(profile)) if profile else None
        ),
        theater_name=theater_name,
        environment_name=environment_name,
        viewer_preset=viewer_preset,
        minovsky_density=conditions.minovsky_density,
        battlefield=conditions.battlefield.model_dump(mode="json"),
    )


class RosterBuilder:
    """本番のエントリー・マッチングと同じ手順で、参加機体のスナップショットを集める.

    DBには書き込まない。読み込んだ ORM オブジェクトを書き換えるため、
    セッションは autoflush=False で作り、コミットしないこと。
    """

    def __init__(self, session: Session) -> None:
        """セッションを受け取る."""
        self.session = session
        self.matching = MatchingService(session)
        self.entries: list[RosterEntry] = []
        self.ace_pilots: list[dict] = []
        self._mobile_suit_ids: set[str] = set()

    def add_mobile_suit(self, spec: UnitSpec) -> None:
        """機体IDで指定した機体を加える.

        Raises:
            ValueError: 機体が無い場合。同じ機体を2回加えた場合
        """
        suit = self.session.get(MobileSuit, _parse_uuid(spec.id, "機体ID"))
        if suit is None:
            raise ValueError(f"機体 {spec.id} が見つかりません。")
        owner = self.session.exec(
            select(Pilot).where(Pilot.user_id == suit.user_id)
        ).first()
        self._add_owned_suit("mobile_suit", suit, owner, spec.team)

    def add_pilot(self, spec: UnitSpec) -> None:
        """パイロットの出撃機体を加える。ID は pilots.id か user_id で指定する.

        Raises:
            ValueError: パイロットか出撃機体が無い場合。同じ機体を2回加えた場合
        """
        pilot = self._find_pilot(spec.id)
        suit = (
            self.session.get(MobileSuit, pilot.active_mobile_suit_id)
            if pilot.active_mobile_suit_id is not None
            else None
        )
        if suit is None and pilot.is_npc:
            # マッチングと同じく、出撃機体が未設定のNPCは所有機の先頭で出撃する。
            suit = self.session.exec(
                select(MobileSuit)
                .where(MobileSuit.user_id == pilot.user_id)
                .where(MobileSuit.side == "ENEMY")
            ).first()
        if suit is None:
            raise ValueError(f"パイロット {pilot.name} の出撃機体が見つかりません。")
        self._add_owned_suit("pilot", suit, pilot, spec.team)

    def add_npcs(self, count: int) -> None:
        """本番の永続化NPCを count 機加える。足りない分は NPC を生成して補う."""
        if count <= 0:
            return
        # 指定済みの機体と重なった分を除いても count 機残るように多めに選ぶ。
        candidates = self.matching.choose_npcs(count + len(self._mobile_suit_ids))
        chosen = [
            (suit, pilot)
            for suit, pilot in candidates
            if str(suit.id) not in self._mobile_suit_ids
        ][:count]
        for suit, pilot in chosen:
            reset_npc_for_battle(suit)
            self._append("npc", suit, pilot, build_npc_entry_snapshot(suit, pilot))

        shortage = count - len(chosen)
        if shortage > 0:
            print(f"  永続化NPCが {shortage} 機足りないため生成します")
        pilot_service = PilotService(self.session)
        for _ in range(shortage):
            suit = self.matching._create_npc_mobile_suit()
            pilot = pilot_service.build_npc_pilot(
                suit.pilot_name or suit.name, suit.personality or "AGGRESSIVE"
            )
            suit.user_id = pilot.user_id
            self._append(
                "generated_npc", suit, pilot, build_npc_entry_snapshot(suit, pilot)
            )

    def add_aces(self, count: int) -> None:
        """エースパイロットをランダムに count 機加える。同じエースは選ばない."""
        if count <= 0:
            return
        aces = get_ace_pilots()
        if count > len(aces):
            print(f"  エースパイロットは {len(aces)} 名しかいないため、全員を加えます")
        for ace_data in random.sample(aces, min(count, len(aces))):
            suit = MatchingService.build_ace_mobile_suit(ace_data)
            self._append("ace", suit, None, build_npc_entry_snapshot(suit))
            record = self.session.get(AcePilot, ace_data["id"])
            if record is not None:
                self.ace_pilots.append(
                    record.model_dump(mode="json", exclude={"created_at", "updated_at"})
                )

    def _find_pilot(self, pilot_ref: str) -> Pilot:
        pilot: Pilot | None = None
        try:
            pilot = self.session.get(Pilot, uuid.UUID(pilot_ref))
        except ValueError:
            pilot = None
        if pilot is None:
            pilot = self.session.exec(
                select(Pilot).where(Pilot.user_id == pilot_ref)
            ).first()
        if pilot is None:
            raise ValueError(f"パイロット {pilot_ref} が見つかりません。")
        return pilot

    def _add_owned_suit(
        self,
        kind: RosterSourceKind,
        suit: MobileSuit,
        pilot: Pilot | None,
        team: str | None,
    ) -> None:
        if str(suit.id) in self._mobile_suit_ids:
            raise ValueError(f"機体 {suit.id} を2回指定しています。")
        if pilot is not None and pilot.is_npc:
            reset_npc_for_battle(suit)
            snapshot = build_npc_entry_snapshot(suit, pilot)
        else:
            WeaponService.resync_mobile_suit_weapons(self.session, suit)
            snapshot = MobileSuitService.build_entry_snapshot(self.session, suit)
        if team is not None:
            snapshot["team_id"] = team
            snapshot["side"] = "PLAYER"
        self._append(kind, suit, pilot, snapshot)

    def _append(
        self,
        kind: RosterSourceKind,
        suit: MobileSuit,
        pilot: Pilot | None,
        snapshot: dict,
    ) -> None:
        self._mobile_suit_ids.add(str(suit.id))
        is_npc = kind in ("npc", "generated_npc", "ace") or bool(
            pilot is not None and pilot.is_npc
        )
        self.entries.append(
            RosterEntry(
                source=RosterSource(
                    kind=kind,
                    mobile_suit_id=str(suit.id),
                    pilot_id=str(pilot.id) if pilot is not None else None,
                    pilot_name=(pilot.name if pilot is not None else suit.pilot_name),
                    ace_id=suit.ace_id,
                ),
                is_npc=is_npc,
                snapshot=snapshot,
            )
        )


def build_roster(session: Session, options: FetchOptions, name: str) -> Roster:
    """指定した機体・NPC・エースと戦域条件からロスターを作る.

    Raises:
        ValueError: 指定が不正な場合。参加機体が2機未満の場合
    """
    validate_roster_name(name)
    conditions = resolve_conditions(
        session, options.theater_id, options.minovsky_density
    )
    builder = RosterBuilder(session)
    for spec in options.mobile_suits:
        builder.add_mobile_suit(spec)
    for spec in options.pilots:
        builder.add_pilot(spec)
    builder.add_aces(options.ace_count)
    builder.add_npcs(options.npc_count)

    if len(builder.entries) < MIN_ROSTER_ENTRIES:
        raise ValueError(
            f"参加機体が {len(builder.entries)} 機です。{MIN_ROSTER_ENTRIES} 機以上を指定してください。"
        )
    return Roster(
        name=name,
        fetched_at=datetime.now(UTC),
        conditions=conditions,
        entries=builder.entries,
        ace_pilots=builder.ace_pilots,
    )


def default_roster_name(now: datetime | None = None) -> str:
    """日時からロスター名を作る（例: 20261005-213000）."""
    return (now or datetime.now()).strftime("%Y%m%d-%H%M%S")


def _parse_uuid(value: str, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise ValueError(f"{label} '{value}' は UUID ではありません。") from exc
