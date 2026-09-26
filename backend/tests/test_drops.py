"""ドロップテーブル・戦利品の抽選のテスト."""

import random
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, col, delete, select

from app.core.auth import get_current_user_optional
from app.models.models import (
    BattleEntry,
    BattleResult,
    BattleRoom,
    BlueprintSource,
    BlueprintTargetType,
    DropScopeType,
    DropTable,
    DropTableEntry,
    MasterBlueprint,
    Mission,
    MobileSuit,
    Pilot,
    PlayerBlueprint,
    Vector3,
    Weapon,
)
from app.services.blueprint_service import UNAVAILABLE_UNLOCK_HINT, BlueprintService
from app.services.drop_service import DropScope, DropService
from main import app

USER_ID = "test_drop_user"
DOM = "mobile_suit:dom"
GELGOOG = "mobile_suit:gelgoog"
GUNDAM = "mobile_suit:gundam"
MISSION_ID = 9002
MISSION_NAME = "Mission 02: 防衛線突破"


class FixedRandom(random.Random):
    """`random()` が固定値を返し、`choices()` の重みを記録する乱数生成器."""

    def __init__(self, value: float) -> None:  # noqa: D107
        super().__init__(0)
        self.value = value
        self.weights: list[int] | None = None

    def random(self) -> float:  # noqa: D102
        return self.value

    def choices(self, population, weights=None, **kwargs):  # type: ignore[no-untyped-def, override]  # noqa: D102
        self.weights = list(weights) if weights is not None else None
        return super().choices(population, weights=weights, **kwargs)


@pytest.fixture(name="pilot")
def pilot_fixture(session: Session) -> Pilot:
    """ジオン所属のパイロットを作成する."""
    pilot = Pilot(user_id=USER_ID, name="Drop Pilot", faction="ZEON", credits=1000)
    session.add(pilot)
    session.commit()
    session.refresh(pilot)
    return pilot


@pytest.fixture(name="mission")
def mission_fixture(session: Session) -> Iterator[Mission]:
    """ソロミッションを作成する。conftest はミッションを削除しないため後始末する."""
    mission = Mission(
        id=MISSION_ID,
        name=MISSION_NAME,
        enemy_config={
            "enemies": [
                {
                    "name": "ボール",
                    "max_hp": 1,
                    "armor": 0,
                    "position": {"x": 300, "y": 0, "z": 0},
                    "weapon": {"power": 1, "range": 100, "accuracy": 1},
                }
            ]
        },
    )
    session.add(mission)
    session.commit()
    yield mission
    session.exec(delete(Mission).where(col(Mission.id) == MISSION_ID))  # type: ignore[call-overload]
    session.commit()


def _make_table(
    session: Session,
    entries: list[tuple[str, int, bool]],
    scope: DropScope | None = None,
    drop_rate: float = 1.0,
    win_rate_multiplier: float = 1.0,
) -> DropTable:
    scope = scope or DropScope.batch()
    table = DropTable(
        scope_type=scope.scope_type.value,
        scope_key=scope.scope_key,
        name="テスト用テーブル",
        drop_rate=drop_rate,
        win_rate_multiplier=win_rate_multiplier,
    )
    session.add(table)
    session.flush()
    for blueprint_id, weight, requires_win in entries:
        session.add(
            DropTableEntry(
                drop_table_id=table.id,
                blueprint_id=blueprint_id,
                weight=weight,
                requires_win=requires_win,
            )
        )
    session.commit()
    return table


def _make_restricted(session: Session, *blueprint_ids: str) -> None:
    for blueprint_id in blueprint_ids:
        blueprint = session.get(MasterBlueprint, blueprint_id)
        assert blueprint is not None
        blueprint.is_standard_issue = False
        session.add(blueprint)
    session.commit()


def _roll(
    session: Session,
    rng: random.Random,
    is_win: bool = True,
    user_id: str = USER_ID,
    scope: DropScope | None = None,
    battle_result_id: uuid.UUID | None = None,
):  # type: ignore[no-untyped-def]
    return DropService.roll(
        session,
        user_id,
        scope or DropScope.batch(),
        is_win=is_win,
        battle_result_id=battle_result_id or uuid.uuid4(),
        rng=rng,
    )


# --- 抽選 ---


def test_effective_drop_rate() -> None:
    """勝利時だけ倍率が掛かり、1を上限とすること."""
    table = DropTable(
        scope_type="BATCH",
        scope_key="x",
        name="t",
        drop_rate=0.4,
        win_rate_multiplier=2,
    )
    assert DropService.effective_drop_rate(table, is_win=False) == 0.4
    assert DropService.effective_drop_rate(table, is_win=True) == 0.8

    table.win_rate_multiplier = 3
    assert DropService.effective_drop_rate(table, is_win=True) == 1.0


def test_roll_grants_blueprint_as_drop(session: Session, pilot: Pilot) -> None:
    """ドロップした設計図が DROP として付与され、バトル結果IDが記録されること."""
    _make_table(session, [(DOM, 1, False)])
    battle_result_id = uuid.uuid4()

    loot = _roll(session, FixedRandom(0.0), battle_result_id=battle_result_id)
    session.commit()

    assert len(loot) == 1
    assert loot[0].model_dump() == {
        "kind": "BLUEPRINT",
        "blueprint_id": DOM,
        "target_type": "MOBILE_SUIT",
        "target_id": "dom",
        "is_new": True,
        "credits_awarded": 0,
    }
    owned = session.exec(
        select(PlayerBlueprint).where(PlayerBlueprint.user_id == USER_ID)
    ).one()
    assert owned.blueprint_id == DOM
    assert owned.source == BlueprintSource.DROP.value
    assert owned.source_battle_id == battle_result_id


def test_roll_duplicate_is_converted_to_credits(session: Session, pilot: Pilot) -> None:
    """所持済みの設計図が出たら換金されること."""
    _make_table(session, [(DOM, 1, False)])
    BlueprintService.grant_blueprint(session, USER_ID, DOM, BlueprintSource.MIGRATION)
    session.commit()
    credit_value = session.get(MasterBlueprint, DOM).duplicate_credit_value  # type: ignore[union-attr]
    assert credit_value > 0

    loot = _roll(session, FixedRandom(0.0))
    session.commit()

    assert loot[0].is_new is False
    assert loot[0].credits_awarded == credit_value
    session.refresh(pilot)
    assert pilot.credits == 1000 + credit_value


def test_roll_misses_when_random_exceeds_rate(session: Session, pilot: Pilot) -> None:
    """乱数がドロップ率以上ならドロップしないこと."""
    _make_table(session, [(DOM, 1, False)], drop_rate=0.5)

    assert _roll(session, FixedRandom(0.5), is_win=False) == []


def test_roll_win_multiplier_raises_rate(session: Session, pilot: Pilot) -> None:
    """勝利時はドロップ率に倍率が掛かること."""
    _make_table(session, [(DOM, 1, False)], drop_rate=0.5, win_rate_multiplier=1.5)

    assert _roll(session, FixedRandom(0.6), is_win=False) == []
    assert len(_roll(session, FixedRandom(0.6), is_win=True)) == 1


def test_roll_requires_win_entries_only_on_win(session: Session, pilot: Pilot) -> None:
    """勝利時のみのエントリーは、敗北時に抽選対象にならないこと."""
    _make_table(session, [(DOM, 3, False), (GELGOOG, 1, True)])

    lose_rng = FixedRandom(0.0)
    _roll(session, lose_rng, is_win=False)
    assert lose_rng.weights == [3]

    win_rng = FixedRandom(0.0)
    _roll(session, win_rng, is_win=True)
    assert win_rng.weights == [3, 1]


def test_roll_no_drop_when_only_win_entries_and_lose(
    session: Session, pilot: Pilot
) -> None:
    """除外した結果、抽選対象が無ければドロップしないこと."""
    _make_table(session, [(GELGOOG, 1, True)])

    assert _roll(session, FixedRandom(0.0), is_win=False) == []


def test_roll_excludes_other_faction(session: Session, pilot: Pilot) -> None:
    """パイロットの勢力では購入できない機体の設計図は抽選対象にならないこと."""
    _make_table(session, [(GUNDAM, 1, False)])

    assert _roll(session, FixedRandom(0.0)) == []

    rng = FixedRandom(0.0)
    _make_table(session, [(GUNDAM, 1, False), (DOM, 1, False)], DropScope.mission(1))
    loot = _roll(session, rng, scope=DropScope.mission(1))
    assert rng.weights == [1]
    assert loot[0].blueprint_id == DOM


def test_roll_allows_weapons_and_unaffiliated_pilot(session: Session) -> None:
    """武器と、勢力の無いパイロットには勢力の制限が掛からないこと."""
    session.add(Pilot(user_id=USER_ID, name="No Faction", faction=""))
    session.commit()
    _make_table(session, [(GUNDAM, 1, False), ("weapon:beam_rifle", 1, False)])

    rng = FixedRandom(0.0)
    _roll(session, rng)

    assert rng.weights == [1, 1]


def test_roll_weight_decides_choice(session: Session, pilot: Pilot) -> None:
    """重みに比例して選ばれること."""
    _make_table(session, [(DOM, 3, False), (GELGOOG, 1, False)])
    rng = random.Random(42)
    counts = {DOM: 0, GELGOOG: 0}
    for _ in range(400):
        loot = _roll(session, rng)
        counts[loot[0].blueprint_id] += 1
    session.rollback()

    assert 250 < counts[DOM] < 350


def test_roll_without_table(session: Session, pilot: Pilot) -> None:
    """適用範囲に対応するテーブルが無ければドロップしないこと."""
    _make_table(session, [(DOM, 1, False)], DropScope.mission(1))

    assert _roll(session, FixedRandom(0.0), scope=DropScope.mission(2)) == []
    assert _roll(session, FixedRandom(0.0), scope=DropScope.batch()) == []


def test_roll_skips_npc_and_unknown_user(session: Session) -> None:
    """NPC パイロットと、パイロットのいないユーザーは抽選しないこと."""
    session.add(Pilot(user_id="npc_user", name="NPC", is_npc=True))
    session.commit()
    _make_table(session, [(DOM, 1, False)])

    assert _roll(session, FixedRandom(0.0), user_id="npc_user") == []
    assert _roll(session, FixedRandom(0.0), user_id="nobody") == []
    assert session.exec(select(PlayerBlueprint)).all() == []


# --- ショップの入手ヒント ---


def test_unlock_hint_lists_missions_and_batch(
    session: Session, pilot: Pilot, mission: Mission
) -> None:
    """入手できるミッション・定期バトルがヒントに並ぶこと."""
    _make_restricted(session, DOM, GELGOOG, GUNDAM)
    _make_table(session, [(DOM, 1, False)], DropScope.mission(MISSION_ID))
    _make_table(session, [(DOM, 3, False), (GELGOOG, 1, True)])

    states = BlueprintService.get_unlock_states(
        session, USER_ID, BlueprintTargetType.MOBILE_SUIT, ["dom", "gelgoog", "gundam"]
    )

    assert states["dom"].unlock_hint == f"『{MISSION_NAME}』・定期バトルでドロップ"
    assert states["gelgoog"].unlock_hint == "定期バトルでドロップ（勝利時のみ）"
    assert states["gundam"].unlock_hint == UNAVAILABLE_UNLOCK_HINT


def test_unlock_hint_marks_win_only_source(
    session: Session, pilot: Pilot, mission: Mission
) -> None:
    """一部の戦闘だけ勝利時のみなら、その戦闘に注記が付くこと."""
    _make_restricted(session, DOM)
    _make_table(session, [(DOM, 1, False)], DropScope.mission(MISSION_ID))
    _make_table(session, [(DOM, 1, True)])

    states = BlueprintService.get_unlock_states(
        session, USER_ID, BlueprintTargetType.MOBILE_SUIT, ["dom"]
    )

    assert (
        states["dom"].unlock_hint
        == f"『{MISSION_NAME}』・定期バトル（勝利時のみ）でドロップ"
    )


def test_unlock_hint_falls_back_to_table_name(session: Session, pilot: Pilot) -> None:
    """ミッションが無いテーブルは、テーブル名で表示すること."""
    _make_restricted(session, DOM)
    _make_table(session, [(DOM, 1, False)], DropScope.mission(424242))

    states = BlueprintService.get_unlock_states(
        session, USER_ID, BlueprintTargetType.MOBILE_SUIT, ["dom"]
    )

    assert states["dom"].unlock_hint == "『テスト用テーブル』でドロップ"


def test_shop_listing_shows_drop_hint(client, session: Session, pilot: Pilot) -> None:  # type: ignore[no-untyped-def]
    """ショップ一覧の unlock_hint にドロップテーブルの内容が出ること."""
    from app.core.auth import get_current_user

    _make_restricted(session, DOM)
    _make_table(session, [(DOM, 1, False)])
    app.dependency_overrides[get_current_user] = lambda: USER_ID

    response = client.get("/api/shop/listings")

    assert response.status_code == 200
    listings = {item["id"]: item for item in response.json()}
    assert listings["dom"]["unlock_hint"] == "定期バトルでドロップ"


# --- 機体・武器マスターの削除 ---


def test_delete_master_blueprint_removes_entries(session: Session) -> None:
    """設計図マスターを削除すると、それを含むエントリーも削除されること."""
    _make_table(session, [(DOM, 1, False), (GELGOOG, 1, False)])

    BlueprintService.delete_master_blueprint(
        session, BlueprintTargetType.MOBILE_SUIT, "dom"
    )
    session.commit()

    remaining = session.exec(select(DropTableEntry.blueprint_id)).all()
    assert remaining == [GELGOOG]


# --- ソロミッション ---


@pytest.fixture(name="solo_client")
def solo_client_fixture(
    client, session: Session, pilot: Pilot, mission: Mission, monkeypatch
):  # type: ignore[no-untyped-def]
    """ログイン済みでソロミッションを実行できるクライアントを返す."""
    session.add(
        MobileSuit(
            user_id=USER_ID,
            name="Zaku",
            max_hp=1000,
            current_hp=1000,
            armor=50,
            mobility=1.5,
            weapons=[Weapon(id="w1", name="MG", power=100, range=500, accuracy=90)],
        )
    )
    session.commit()
    monkeypatch.setattr("main.offload_battle_log_to_gcs", lambda *args: None)
    app.dependency_overrides[get_current_user_optional] = lambda: USER_ID
    return client


def test_simulate_records_loot(solo_client, session: Session) -> None:  # type: ignore[no-untyped-def]
    """ソロミッションの結果に戦利品が記録され、レスポンスに含まれること."""
    _make_table(session, [(DOM, 1, False)], DropScope.mission(MISSION_ID))

    response = solo_client.post(f"/api/battle/simulate?mission_id={MISSION_ID}")

    assert response.status_code == 200
    loot = response.json()["rewards"]["loot"]
    assert [item["blueprint_id"] for item in loot] == [DOM]

    result = session.exec(
        select(BattleResult).where(BattleResult.user_id == USER_ID)
    ).one()
    assert result.loot == loot
    owned = session.exec(
        select(PlayerBlueprint).where(PlayerBlueprint.user_id == USER_ID)
    ).one()
    assert owned.source_battle_id == result.id

    history = solo_client.get("/api/battles").json()
    assert history[0]["loot"] == loot
    detail = solo_client.get(f"/api/battles/{result.id}").json()
    assert detail["loot"] == loot


def test_simulate_without_table_records_empty_loot(
    solo_client, session: Session
) -> None:  # type: ignore[no-untyped-def]
    """テーブルが無いミッションでは、空の戦利品が記録されること."""
    response = solo_client.post(f"/api/battle/simulate?mission_id={MISSION_ID}")

    assert response.status_code == 200
    assert response.json()["rewards"]["loot"] == []
    result = session.exec(
        select(BattleResult).where(BattleResult.user_id == USER_ID)
    ).one()
    assert result.loot == []


# --- 定期バトル ---


def _make_batch_entry(session: Session, room: BattleRoom, user_id: str) -> BattleEntry:
    suit = MobileSuit(
        user_id=user_id,
        name=f"MS {user_id}",
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w1", name="MG", power=100, range=500, accuracy=80)],
    )
    session.add(suit)
    session.commit()
    session.refresh(suit)
    entry = BattleEntry(
        user_id=user_id,
        room_id=room.id,
        mobile_suit_id=suit.id,
        mobile_suit_snapshot=suit.model_dump(mode="json"),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def _save_batch(
    session: Session,
    entries: list[BattleEntry],
    room: BattleRoom,
    rng: random.Random | None = None,
) -> None:
    from scripts.run_batch import _convert_snapshot_to_mobile_suit, _save_battle_results

    units = [
        _convert_snapshot_to_mobile_suit(dict(e.mobile_suit_snapshot)) for e in entries
    ]
    for unit in units:
        unit.team_id = str(unit.id)
    simulator = MagicMock()
    simulator.units = units
    simulator.logs = []
    simulator.obstacles = []
    simulator.map_bounds = (0.0, 1000.0)
    _save_battle_results(
        session=session,
        room=room,
        player_entries=entries,
        npc_entries=[],
        simulator=simulator,
        primary_player_win=True,
        player_unit=units[0],
        enemy_units=units[1:],
        rng=rng or FixedRandom(0.0),
    )


@pytest.fixture(name="room")
def room_fixture(session: Session) -> BattleRoom:
    """定期バトルのルームを作成する."""
    room = BattleRoom(status="WAITING", scheduled_at=datetime.now(UTC))
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


def test_batch_records_loot_per_player(
    session: Session, pilot: Pilot, room: BattleRoom
) -> None:
    """定期バトルでプレイヤーごとに抽選され、バトル結果に記録されること."""
    session.add(Pilot(user_id="other_user", name="Other", faction="ZEON"))
    session.commit()
    _make_table(session, [(DOM, 1, False)])
    entries = [
        _make_batch_entry(session, room, USER_ID),
        _make_batch_entry(session, room, "other_user"),
    ]

    _save_batch(session, entries, room)

    results = session.exec(
        select(BattleResult).where(BattleResult.room_id == room.id)
    ).all()
    assert len(results) == 2
    owned_by_user = {
        owned.user_id: owned for owned in session.exec(select(PlayerBlueprint)).all()
    }
    for result in results:
        assert result.loot is not None
        assert [item["blueprint_id"] for item in result.loot] == [DOM]
        assert owned_by_user[result.user_id].source_battle_id == result.id  # type: ignore[index]


def test_batch_drop_error_does_not_stop_others(
    session: Session, pilot: Pilot, room: BattleRoom, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """1人の抽選でエラーが起きても、他のプレイヤーとバトル結果の保存を止めないこと."""
    session.add(Pilot(user_id="other_user", name="Other", faction="ZEON"))
    session.commit()
    _make_table(session, [(DOM, 1, False)])
    entries = [
        _make_batch_entry(session, room, USER_ID),
        _make_batch_entry(session, room, "other_user"),
    ]
    original_roll = DropService.roll

    def _failing_roll(session, user_id, *args, **kwargs):  # type: ignore[no-untyped-def]
        if user_id == USER_ID:
            raise RuntimeError("boom")
        return original_roll(session, user_id, *args, **kwargs)

    monkeypatch.setattr(DropService, "roll", staticmethod(_failing_roll))

    _save_batch(session, entries, room)

    loot_by_user = {
        result.user_id: result.loot
        for result in session.exec(
            select(BattleResult).where(BattleResult.room_id == room.id)
        ).all()
    }
    assert loot_by_user[USER_ID] == []
    assert [item["blueprint_id"] for item in loot_by_user["other_user"]] == [DOM]  # type: ignore[union-attr]


def test_batch_loot_does_not_depend_on_entry_order(
    session: Session, pilot: Pilot
) -> None:
    """同じ乱数なら、エントリーの並び順によらず同じ抽選結果になること."""
    other_users = [f"user_{i}" for i in range(5)]
    for user_id in other_users:
        session.add(Pilot(user_id=user_id, name=user_id, faction="ZEON"))
    session.commit()
    _make_table(session, [(DOM, 1, False), (GELGOOG, 1, False)], drop_rate=0.5)

    loot_by_order = []
    for reverse in (False, True):
        room = BattleRoom(status="WAITING", scheduled_at=datetime.now(UTC))
        session.add(room)
        session.commit()
        entries = [
            _make_batch_entry(session, room, user_id)
            for user_id in [USER_ID, *other_users]
        ]
        if reverse:
            entries.reverse()
        _save_batch(session, entries, room, rng=random.Random(7))
        loot_by_order.append(
            {
                # 2回目は所持済みで換金されるため、設計図IDだけを比べる。
                result.user_id: [item["blueprint_id"] for item in result.loot or []]
                for result in session.exec(
                    select(BattleResult).where(BattleResult.room_id == room.id)
                ).all()
            }
        )

    assert loot_by_order[0] == loot_by_order[1]
    assert any(loot_by_order[0].values())


# --- シード ---


def test_seed_drop_tables_is_idempotent(session: Session) -> None:
    """シードが定期バトルのテーブルを作り、再実行しても重複しないこと."""
    from scripts.seed.seed_drop_tables import seed_drop_tables

    first = seed_drop_tables(session)
    session.commit()
    second = seed_drop_tables(session)
    session.commit()

    table = session.exec(
        select(DropTable).where(DropTable.scope_type == DropScopeType.BATCH.value)
    ).one()
    assert table.drop_rate == 0.3
    assert table.win_rate_multiplier == 1.5
    entries = {
        e.blueprint_id: (e.weight, e.requires_win)
        for e in session.exec(select(DropTableEntry)).all()
    }
    # テスト用のマスターデータには zaku_ii_f が無いため投入されない。
    assert entries == {DOM: (3, False), GELGOOG: (1, True), GUNDAM: (1, True)}
    assert first["inserted"] == 3
    assert first["missing_blueprint"] == 1
    assert second["inserted"] == 0
    assert second["skipped"] == 3
