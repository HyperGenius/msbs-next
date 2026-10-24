"""本番DBから参加機体と戦域条件を読み、ロスターを作る.

このモジュールは `app` を import する。本番DBに接続するときは、
import する前に `readonly_db.use_readonly_database()` を呼ぶこと。
"""

import random
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.core.gamedata import get_ace_pilots
from app.models.models import (
    AcePilot,
    MasterEnvironment,
    MasterTheater,
    Mission,
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
from app.services.retreat_support_mission import build_retreat_support_mission
from app.services.theater_service import BattleConditions, TheaterService
from app.services.weapon_service import WeaponService
from scripts.simulation.local_sim.roster import (
    Roster,
    RosterConditions,
    RosterEntry,
    RosterEnvironmentProfile,
    RosterMission,
    RosterSource,
    RosterSourceKind,
    validate_roster_name,
)

MIN_ROSTER_ENTRIES = 2
# 作戦では敵機を作戦マスターから出すため、プレイヤー機は1機でよい。
MIN_MISSION_ROSTER_ENTRIES = 1

# --mission-builder で選べる、リポジトリの作戦マスターの定義。
# 本番の missions に反映する前の作戦を試すときに使う。
MISSION_BUILDERS: dict[str, Callable[[], Mission]] = {
    "retreat_support": build_retreat_support_mission,
}


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
    # 必ず参加させるエースの ID。ace_count と併用すると、指定したエースを含めて ace_count 機にする。
    ace_ids: list[str] = field(default_factory=list)
    theater_id: str | None = None
    # None なら戦域の基準濃度。戦域も無ければ 0。
    minovsky_density: float | None = None
    # 本番の作戦マスター（missions.id）。mission_builder とは併用できない。
    mission_id: int | None = None
    # MISSION_BUILDERS の名前。
    mission_builder: str | None = None

    @property
    def has_mission(self) -> bool:
        """作戦の戦闘か."""
        return self.mission_id is not None or self.mission_builder is not None


def resolve_conditions(
    session: Session,
    theater_id: str | None,
    minovsky_density: float | None,
    environment: str | None = None,
) -> RosterConditions:
    """戦域と濃度から、ロスターに保存する戦域条件を作る.

    戦域が無いときは environment（省略時は宇宙）で戦う。作戦では作戦の環境を渡す。

    Raises:
        ValueError: 戦域、または戦域の環境タイプがマスターに無い場合
    """
    if minovsky_density is not None and not 0.0 <= minovsky_density <= 1.0:
        raise ValueError("ミノフスキー濃度は 0〜1 で指定してください。")
    theater: MasterTheater | None = None
    if theater_id is None:
        conditions = BattleConditions(minovsky_density=minovsky_density or 0.0)
        if environment is not None:
            conditions = replace(conditions, environment=environment)
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
            raise ValueError(
                f"パイロット {pilot.name} の出撃機体（pilots.active_mobile_suit_id）が"
                "見つかりません。プレイヤーの出撃機体はエントリーごとに選ぶため、"
                "この項目は設定されないことがあります。--ms <機体ID> で機体を直接指定してください。"
            )
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

    def add_aces(self, count: int, ace_ids: list[str] | None = None) -> None:
        """エースパイロットを加える.

        ace_ids のエースは必ず加え、count がそれより多ければ残りをランダムに選ぶ。
        同じエースは選ばない。

        Raises:
            ValueError: 指定したエースが無い場合。同じエースを2回指定した場合
        """
        ace_ids = ace_ids or []
        aces = get_ace_pilots()
        by_id = {a["id"]: a for a in aces}
        if len(set(ace_ids)) != len(ace_ids):
            raise ValueError("同じエースを2回指定しています。")
        unknown = [i for i in ace_ids if i not in by_id]
        if unknown:
            raise ValueError(
                f"エース {', '.join(unknown)} が見つかりません"
                f"（{', '.join(sorted(by_id))}）。"
            )
        chosen = [by_id[i] for i in ace_ids]
        random_count = count - len(chosen)
        if random_count > 0:
            rest = [a for a in aces if a["id"] not in ace_ids]
            if random_count > len(rest):
                print(
                    f"  エースパイロットは {len(aces)} 名しかいないため、全員を加えます"
                )
            chosen += random.sample(rest, min(random_count, len(rest)))
        for ace_data in chosen:
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


def load_mission(session: Session, options: FetchOptions) -> RosterMission | None:
    """作戦マスターを本番の missions か、リポジトリの定義から読む.

    Raises:
        ValueError: 作戦が無い場合。作戦IDと定義の名前を両方指定した場合
    """
    if options.mission_id is not None and options.mission_builder is not None:
        raise ValueError("--mission と --mission-builder は併用できません。")
    if options.mission_id is not None:
        mission = session.get(Mission, options.mission_id)
        if mission is None:
            raise ValueError(f"作戦 {options.mission_id} が見つかりません。")
        source, builder = "production", None
    elif options.mission_builder is not None:
        build = MISSION_BUILDERS.get(options.mission_builder)
        if build is None:
            names = ", ".join(sorted(MISSION_BUILDERS))
            raise ValueError(
                f"作戦の定義 '{options.mission_builder}' はありません（{names}）。"
            )
        mission = build()
        source, builder = "builder", options.mission_builder
    else:
        return None
    return RosterMission(
        source=source,
        builder=builder,
        master=mission.model_dump(mode="json", exclude={"created_at", "updated_at"}),
    )


def _validate_mission_options(options: FetchOptions) -> None:
    """本番の作戦ルームと同じく、プレイヤー機だけを同じチームで出す指定か確かめる.

    Raises:
        ValueError: NPC・エース・チームを指定した場合
    """
    if options.npc_count or options.ace_count or options.ace_ids:
        raise ValueError(
            "作戦では敵機を作戦マスターから出します。--npc / --ace / --ace-id は併用できません。"
        )
    teams = [s for s in [*options.mobile_suits, *options.pilots] if s.team]
    if teams:
        raise ValueError(
            "作戦ではプレイヤー機は全員同じチームで出ます。"
            f"チームの指定（{', '.join(f'{s.id}:{s.team}' for s in teams)}）を外してください。"
        )


def build_roster(session: Session, options: FetchOptions, name: str) -> Roster:
    """指定した機体・NPC・エースと戦域条件からロスターを作る.

    作戦を指定したときは、プレイヤー機と作戦マスターを保存する。
    友軍・敵機は `run` で作戦マスターから組み立てる。

    Raises:
        ValueError: 指定が不正な場合。参加機体が足りない場合
    """
    validate_roster_name(name)
    if options.has_mission:
        _validate_mission_options(options)
    mission = load_mission(session, options)
    conditions = resolve_conditions(
        session,
        options.theater_id,
        options.minovsky_density,
        environment=mission.master["environment"] if mission else None,
    )
    builder = RosterBuilder(session)
    for spec in options.mobile_suits:
        builder.add_mobile_suit(spec)
    for spec in options.pilots:
        builder.add_pilot(spec)
    builder.add_aces(options.ace_count, options.ace_ids)
    builder.add_npcs(options.npc_count)

    min_entries = MIN_MISSION_ROSTER_ENTRIES if mission else MIN_ROSTER_ENTRIES
    if len(builder.entries) < min_entries:
        raise ValueError(
            f"参加機体が {len(builder.entries)} 機です。{min_entries} 機以上を指定してください。"
        )
    return Roster(
        name=name,
        fetched_at=datetime.now(UTC),
        conditions=conditions,
        entries=builder.entries,
        ace_pilots=builder.ace_pilots,
        mission=mission,
    )


def default_roster_name(now: datetime | None = None) -> str:
    """日時からロスター名を作る（例: 20261005-213000）."""
    return (now or datetime.now()).strftime("%Y%m%d-%H%M%S")


def _parse_uuid(value: str, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise ValueError(f"{label} '{value}' は UUID ではありません。") from exc
