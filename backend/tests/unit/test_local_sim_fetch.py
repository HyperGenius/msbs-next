"""ローカルシミュレータの fetch（ロスターの作成と Read Only 接続）のテスト."""

import json
import os
import sys

import pytest
from sqlalchemy import func
from sqlalchemy.engine import make_url
from sqlmodel import Session, select

import app.db as app_db
from app.models.models import MobileSuit, Pilot, PlayerWeapon, Vector3, Weapon
from app.services.matching_service import MatchingService
from scripts.simulation.local_sim import readonly_db
from scripts.simulation.local_sim.fetch import (
    FetchOptions,
    RosterBuilder,
    UnitSpec,
    build_roster,
    parse_unit_spec,
    resolve_conditions,
)
from scripts.simulation.local_sim.roster import (
    Roster,
    load_roster,
    roster_path,
    save_roster,
)


def _suit(name: str, user_id: str, side: str = "PLAYER", **kwargs) -> MobileSuit:
    fields = {
        "name": name,
        "max_hp": 800,
        "current_hp": 800,
        "armor": 40,
        "mobility": 1.0,
        "position": Vector3(x=0, y=0, z=0),
        "weapons": [Weapon(id="w1", name="Rifle", power=100, range=500, accuracy=70)],
        "side": side,
        "user_id": user_id,
    }
    return MobileSuit(**(fields | kwargs))


def _player(session: Session, user_id: str, suit_name: str = "Zaku II") -> Pilot:
    suit = _suit(suit_name, user_id, master_mobile_suit_id="zaku_ii")
    pilot = Pilot(user_id=user_id, name=f"pilot-{user_id}", active_mobile_suit_id=None)
    session.add(suit)
    session.add(pilot)
    session.flush()
    pilot.active_mobile_suit_id = suit.id
    session.add(pilot)
    session.commit()
    return pilot


def _npc(session: Session, user_id: str, with_active: bool = True) -> Pilot:
    suit = _suit("Gouf (NPC)", user_id, side="ENEMY", current_hp=10)
    pilot = Pilot(user_id=user_id, name=f"npc-{user_id}", is_npc=True, level=4)
    session.add(suit)
    session.add(pilot)
    session.flush()
    if with_active:
        pilot.active_mobile_suit_id = suit.id
        session.add(pilot)
    session.commit()
    return pilot


def _db_state(session: Session) -> dict:
    """DB の書き込みを検出するため、行数と更新されうる列を集める."""
    session.expire_all()
    return {
        "pilots": sorted(
            (str(p.id), str(p.active_mobile_suit_id), p.updated_at.isoformat())
            for p in session.exec(select(Pilot)).all()
        ),
        "mobile_suits": sorted(
            (str(s.id), s.current_hp, json.dumps(s.model_dump(mode="json")["position"]))
            for s in session.exec(select(MobileSuit)).all()
        ),
        "player_weapons": session.exec(
            select(func.count()).select_from(PlayerWeapon)
        ).one(),
    }


# --- 引数の解析 ---


def test_parse_unit_spec_with_and_without_team() -> None:
    """`<ID>[:<チーム>]` をIDとチームに分けること."""
    assert parse_unit_spec("abc") == UnitSpec(id="abc", team=None)
    assert parse_unit_spec("abc:A") == UnitSpec(id="abc", team="A")


@pytest.mark.parametrize("value", ["", ":A", "abc:"])
def test_parse_unit_spec_rejects_empty_parts(value: str) -> None:
    """ID かチームが空なら ValueError にすること."""
    with pytest.raises(ValueError):
        parse_unit_spec(value)


# --- 機体の選択 ---


def test_build_roster_collects_players_npcs_and_aces(session: Session) -> None:
    """機体・パイロット・NPC・エースを指定してロスターを作れること."""
    p1 = _player(session, "user_a")
    p2 = _player(session, "user_b", suit_name="Unknown Suit")
    _npc(session, "npc-1")
    options = FetchOptions(
        mobile_suits=[UnitSpec(str(p1.active_mobile_suit_id), team="A")],
        pilots=[UnitSpec(p2.user_id, team="A")],
        npc_count=3,
        ace_count=1,
    )

    with Session(app_db.engine, autoflush=False) as fetch_session:
        roster = build_roster(fetch_session, options, "test_roster")

    kinds = [e.source.kind for e in roster.entries]
    assert kinds == [
        "mobile_suit",
        "pilot",
        "ace",
        "npc",
        "generated_npc",
        "generated_npc",
    ]
    by_kind = {e.source.kind: e for e in roster.entries}

    player = by_kind["mobile_suit"]
    assert player.is_npc is False
    assert player.snapshot["team_id"] == "A"
    assert player.snapshot["side"] == "PLAYER"
    # build_entry_snapshot() と同じく、地形適正は機体マスターから入る。
    assert player.snapshot["terrain_adaptability"]["UNDERWATER"] == "C"
    assert by_kind["pilot"].source.pilot_name == "pilot-user_b"

    npc = by_kind["npc"]
    assert npc.is_npc is True
    assert npc.snapshot["npc_pilot_level"] == 4
    assert npc.snapshot["current_hp"] == npc.snapshot["max_hp"]
    assert npc.snapshot["team_id"] is None

    ace = by_kind["ace"]
    assert ace.is_npc is True
    assert ace.snapshot["is_ace"] is True
    assert [a["id"] for a in roster.ace_pilots] == [ace.source.ace_id]

    generated = by_kind["generated_npc"]
    assert generated.snapshot["npc_pilot_level"] == 1
    assert generated.source.pilot_name is not None


def test_build_roster_does_not_write_to_db(session: Session) -> None:
    """出撃機体が未設定のNPCを選んでも、DB の内容が変わらないこと."""
    p1 = _player(session, "user_a")
    npc = _npc(session, "npc-unset", with_active=False)
    before = _db_state(session)

    with Session(app_db.engine, autoflush=False) as fetch_session:
        roster = build_roster(
            fetch_session,
            FetchOptions(pilots=[UnitSpec(str(p1.id))], npc_count=1, ace_count=1),
            "no_write",
        )
        fetch_session.rollback()

    npc_entry = next(e for e in roster.entries if e.source.kind == "npc")
    assert npc_entry.source.pilot_id == str(npc.id)
    assert _db_state(session) == before


def test_choose_npcs_uses_first_owned_suit_without_saving(session: Session) -> None:
    """choose_npcs() は出撃機体が未設定のNPCに所有機の先頭を使い、保存しないこと."""
    npc = _npc(session, "npc-unset", with_active=False)

    [(suit, pilot)] = MatchingService(session).choose_npcs(1)

    assert pilot.id == npc.id
    assert suit.user_id == npc.user_id
    assert pilot.active_mobile_suit_id is None
    assert not session.dirty


def test_select_npcs_for_room_still_saves_active_suit(session: Session) -> None:
    """select_npcs_for_room() は従来どおり出撃機体を保存すること."""
    _npc(session, "npc-unset", with_active=False)

    [(suit, pilot)] = MatchingService(session).select_npcs_for_room(1)
    session.commit()
    session.refresh(pilot)

    assert pilot.active_mobile_suit_id == suit.id


def test_add_npcs_skips_suits_already_in_roster(session: Session) -> None:
    """--pilot で指定したNPCの機体を --npc で重ねて選ばないこと."""
    npc = _npc(session, "npc-1")
    with Session(app_db.engine, autoflush=False) as fetch_session:
        builder = RosterBuilder(fetch_session)
        builder.add_pilot(UnitSpec(npc.user_id))
        builder.add_npcs(1)

    assert [e.source.kind for e in builder.entries] == ["pilot", "generated_npc"]
    # NPC のパイロットを指定したときは、マッチングと同じ NPC のスナップショットになる。
    assert builder.entries[0].is_npc is True
    assert builder.entries[0].snapshot["npc_pilot_level"] == 4


def test_add_aces_does_not_pick_same_ace_twice(session: Session) -> None:
    """エースを複数選ぶとき、同じエースを重ねないこと."""
    with Session(app_db.engine, autoflush=False) as fetch_session:
        builder = RosterBuilder(fetch_session)
        builder.add_aces(100)

    ace_ids = [e.source.ace_id for e in builder.entries]
    assert len(ace_ids) == len(set(ace_ids)) == len(builder.ace_pilots)


def test_add_mobile_suit_rejects_duplicates(session: Session) -> None:
    """同じ機体を2回指定したら ValueError にすること."""
    p1 = _player(session, "user_a")
    spec = UnitSpec(str(p1.active_mobile_suit_id))
    with Session(app_db.engine, autoflush=False) as fetch_session:
        builder = RosterBuilder(fetch_session)
        builder.add_mobile_suit(spec)
        with pytest.raises(ValueError, match="2回"):
            builder.add_mobile_suit(spec)


def test_add_pilot_without_active_suit_fails(session: Session) -> None:
    """出撃機体が未設定のパイロットは ValueError にすること."""
    session.add(Pilot(user_id="user_x", name="x"))
    session.commit()
    with Session(app_db.engine, autoflush=False) as fetch_session:
        with pytest.raises(ValueError, match="出撃機体"):
            RosterBuilder(fetch_session).add_pilot(UnitSpec("user_x"))


def test_build_roster_requires_two_entries(session: Session) -> None:
    """参加機体が2機未満なら ValueError にすること."""
    p1 = _player(session, "user_a")
    with pytest.raises(ValueError, match="2 機以上"):
        build_roster(session, FetchOptions(pilots=[UnitSpec(str(p1.id))]), "solo")


# --- 戦域条件 ---


def test_resolve_conditions_defaults_to_space() -> None:
    """戦域を指定しなければ既定の条件（宇宙・濃度0）になること."""
    conditions = resolve_conditions(None, None, None)  # type: ignore[arg-type]
    assert conditions.theater_id is None
    assert conditions.environment == "SPACE"
    assert conditions.minovsky_density == 0.0
    assert conditions.environment_profile is None


def test_resolve_conditions_uses_theater_master(session: Session) -> None:
    """戦域を指定すると、戦域・環境タイプのマスター値が入ること."""
    conditions = resolve_conditions(session, "southeast_asia_jungle", None)
    assert conditions.theater_id == "southeast_asia_jungle"
    assert conditions.environment == "FOREST"
    assert conditions.environment_profile is not None
    assert conditions.environment_profile.environment_id == "FOREST"
    # 濃度を省略すると戦域の基準濃度になる。
    assert conditions.minovsky_density == 0.6

    assert resolve_conditions(session, "solomon", 0.1).minovsky_density == 0.1


def test_resolve_conditions_rejects_unknown_theater(session: Session) -> None:
    """マスターに無い戦域は ValueError にすること."""
    with pytest.raises(ValueError, match="戦域"):
        resolve_conditions(session, "no_such_theater", None)


def test_resolve_conditions_rejects_out_of_range_minovsky(session: Session) -> None:
    """濃度が 0〜1 の外なら ValueError にすること."""
    with pytest.raises(ValueError, match="0〜1"):
        resolve_conditions(session, None, 1.5)


# --- ロスターの保存 ---


def test_save_and_load_roster_round_trip(session: Session, tmp_path) -> None:
    """整形した JSON で保存し、読み戻せること。上書きは明示したときだけ."""
    p1 = _player(session, "user_a")
    _npc(session, "npc-1")
    roster = build_roster(
        session,
        FetchOptions(pilots=[UnitSpec(str(p1.id))], npc_count=1),
        "round_trip",
    )

    path = save_roster(roster, rosters_dir=tmp_path)
    text = path.read_text(encoding="utf-8")
    assert path == tmp_path / "round_trip.json"
    assert text.startswith("{\n  ")
    assert load_roster(
        "round_trip", rosters_dir=tmp_path
    ) == Roster.model_validate_json(text)

    with pytest.raises(FileExistsError):
        save_roster(roster, rosters_dir=tmp_path)
    save_roster(roster, rosters_dir=tmp_path, overwrite=True)


@pytest.mark.parametrize("name", ["../escape", "a/b", "", ".hidden"])
def test_roster_path_rejects_unsafe_names(name: str, tmp_path) -> None:
    """保存先の外に出る名前を受け付けないこと."""
    with pytest.raises(ValueError):
        roster_path(name, tmp_path)


# --- Read Only 接続 ---


def test_readonly_url_adds_read_only_option() -> None:
    """接続文字列に default_transaction_read_only=on を付けること."""
    url = make_url(
        readonly_db.readonly_url_with_options(
            "postgresql://ro:secret@host/db?sslmode=require"
        )
    )
    assert url.query["options"] == "-c default_transaction_read_only=on"
    assert url.query["sslmode"] == "require"
    assert url.password == "secret"


def test_readonly_url_keeps_existing_options() -> None:
    """Neon の endpoint 指定など、既存の options を残すこと."""
    url = make_url(
        readonly_db.readonly_url_with_options(
            "postgresql://ro:pw@host/db?options=endpoint%3Dep-123"
        )
    )
    assert url.query["options"] == (
        "endpoint=ep-123 -c default_transaction_read_only=on"
    )


def test_use_readonly_database_requires_env(monkeypatch) -> None:
    """NEON_READONLY_DATABASE_URL が未設定ならエラーにし、NEON_DATABASE_URL を使わないこと."""
    monkeypatch.setattr(readonly_db, "load_dotenv", lambda *_a, **_k: None)
    monkeypatch.delitem(sys.modules, "app.db")
    monkeypatch.delenv(readonly_db.READONLY_URL_ENV, raising=False)
    monkeypatch.setenv(readonly_db.WRITABLE_URL_ENV, "postgresql://rw@host/db")

    with pytest.raises(readonly_db.ReadOnlyConfigError, match="NEON_READONLY"):
        readonly_db.use_readonly_database()
    assert os.environ[readonly_db.WRITABLE_URL_ENV] == "postgresql://rw@host/db"


def test_use_readonly_database_replaces_writable_url(monkeypatch) -> None:
    """app.db が読む接続文字列を Read Only のものに差し替えること."""
    monkeypatch.setattr(readonly_db, "load_dotenv", lambda *_a, **_k: None)
    monkeypatch.delitem(sys.modules, "app.db")
    monkeypatch.setenv(readonly_db.READONLY_URL_ENV, "postgresql://ro:pw@host/db")
    monkeypatch.setenv(readonly_db.WRITABLE_URL_ENV, "postgresql://rw:pw@host/db")

    readonly_db.use_readonly_database()

    url = make_url(os.environ[readonly_db.WRITABLE_URL_ENV])
    assert url.username == "ro"
    assert url.query["options"] == "-c default_transaction_read_only=on"


def test_use_readonly_database_refuses_after_app_db_import(monkeypatch) -> None:
    """app.db が先に import されていたら、書き込み可能なエンジンが残るためエラーにすること."""
    monkeypatch.setenv(readonly_db.READONLY_URL_ENV, "postgresql://ro:pw@host/db")
    assert "app.db" in sys.modules
    with pytest.raises(readonly_db.ReadOnlyConfigError, match="app.db"):
        readonly_db.use_readonly_database()


def test_add_pilot_npc_without_active_suit_uses_owned_suit(session: Session) -> None:
    """出撃機体が未設定のNPCパイロットは、マッチングと同じく所有機で参加すること."""
    npc = _npc(session, "npc-unset", with_active=False)
    with Session(app_db.engine, autoflush=False) as fetch_session:
        builder = RosterBuilder(fetch_session)
        builder.add_pilot(UnitSpec(npc.user_id))

    [entry] = builder.entries
    assert entry.is_npc is True
    assert entry.snapshot["user_id"] == npc.user_id
