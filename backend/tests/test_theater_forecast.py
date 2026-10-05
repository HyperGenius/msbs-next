"""戦域予報 API のテスト."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.models import (
    BattleEntry,
    BattleResult,
    BattleRoom,
    MasterTheater,
    MinovskyLevel,
    MobileSuit,
    Vector3,
    Weapon,
)
from app.services.battle_execution import BattleOutcome, snapshot_to_mobile_suit
from app.services.battle_room_service import BattleRoomService
from app.services.theater_forecast_service import (
    MINOVSKY_LEVEL_LOW_MAX,
    MINOVSKY_LEVEL_MEDIUM_MAX,
    TheaterForecastService,
    minovsky_level,
)
from app.services.theater_service import TheaterService
from scripts import run_batch

USER_ID = "test_forecast_user"
# 2026-10-01 は東南アジア密林、翌日はソロモン宙域の開催日。
CURRENT_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _make_open_room(
    session: Session, theater_id: str | None, minovsky_density: float | None
) -> BattleRoom:
    room = BattleRoom(
        status="OPEN",
        scheduled_at=CURRENT_AT,
        theater_id=theater_id,
        minovsky_density=minovsky_density,
    )
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


def _deactivate(session: Session, theater_id: str) -> None:
    theater = session.get(MasterTheater, theater_id)
    assert theater is not None
    theater.is_active = False
    session.add(theater)
    session.commit()


# --- 濃度の段階 ---


@pytest.mark.parametrize(
    ("density", "expected"),
    [
        (0.0, MinovskyLevel.LOW),
        (MINOVSKY_LEVEL_LOW_MAX - 0.01, MinovskyLevel.LOW),
        (MINOVSKY_LEVEL_LOW_MAX, MinovskyLevel.MEDIUM),
        (MINOVSKY_LEVEL_MEDIUM_MAX - 0.01, MinovskyLevel.MEDIUM),
        (MINOVSKY_LEVEL_MEDIUM_MAX, MinovskyLevel.HIGH),
        (1.0, MinovskyLevel.HIGH),
    ],
)
def test_minovsky_level(density: float, expected: MinovskyLevel) -> None:
    """濃度は しきい値未満で LOW、次のしきい値未満で MEDIUM、それ以上で HIGH."""
    assert minovsky_level(density) == expected


# --- API ---


def test_forecast_returns_current_room_and_upcoming(
    client: TestClient, session: Session
) -> None:
    """今回はルームに保存した値、次回以降は開催日から計算した値を返す."""
    # 計算では出ない濃度をルームに入れ、ルームの値を返すことを確かめる。
    _make_open_room(session, "southeast_asia_jungle", 0.99)

    response = client.get("/api/theaters/forecast?days=3")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    current = body[0]
    assert current["is_current"] is True
    assert current["scheduled_at"] == "2026-10-01T12:00:00Z"
    assert current["theater_id"] == "southeast_asia_jungle"
    assert current["theater_name"] == "東南アジア密林"
    assert current["environment_id"] == "FOREST"
    assert current["environment_name"] == "森林"
    assert current["default_terrain_grade"] == "A"
    assert current["minovsky_density"] == 0.99
    assert current["minovsky_level"] == "HIGH"
    assert current["hint"] == "格闘・索敵に強い機体が有利。長距離射撃は不利"

    for offset, item in enumerate(body[1:], start=1):
        expected = TheaterService.resolve_for_date(
            session, date(2026, 10, 1) + timedelta(days=offset)
        )
        assert item["is_current"] is False
        assert item["scheduled_at"] == (
            (CURRENT_AT + timedelta(days=offset)).isoformat().replace("+00:00", "Z")
        )
        assert item["theater_id"] == expected.theater_id
        assert item["environment_id"] == expected.environment_id
        assert item["minovsky_density"] == expected.minovsky_density
        assert item["minovsky_level"] == minovsky_level(expected.minovsky_density)
    assert body[1]["theater_name"] == "ソロモン宙域"
    assert body[1]["environment_name"] == "宇宙"


def test_forecast_defaults_to_three_days(client: TestClient, session: Session) -> None:
    """Days を省略すると3回分を返す."""
    _make_open_room(session, "southeast_asia_jungle", 0.6)

    assert len(client.get("/api/theaters/forecast").json()) == 3


@pytest.mark.parametrize("days", [0, 8])
def test_forecast_rejects_days_out_of_range(client: TestClient, days: int) -> None:
    """Days は1〜7."""
    response = client.get(f"/api/theaters/forecast?days={days}")
    assert response.status_code == 422


def test_forecast_without_open_room_does_not_create_room(session: Session) -> None:
    """OPEN ルームが無ければ次の開催を計算し、ルームは作らない."""
    now = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)

    forecasts = TheaterForecastService.forecast(session, 2, now=now)

    assert session.exec(select(BattleRoom)).all() == []
    assert [f.scheduled_at for f in forecasts] == [
        CURRENT_AT,
        CURRENT_AT + timedelta(days=1),
    ]
    assert forecasts[0].is_current
    expected = TheaterService.resolve_for_date(session, date(2026, 10, 1))
    assert forecasts[0].theater_id == expected.theater_id
    assert forecasts[0].minovsky_density == expected.minovsky_density


def test_forecast_is_empty_without_active_theaters(
    client: TestClient, session: Session
) -> None:
    """有効な戦域が無ければ空の配列を返す."""
    _deactivate(session, "solomon")
    _deactivate(session, "southeast_asia_jungle")
    BattleRoomService.get_or_create_open_room(session)

    assert client.get("/api/theaters/forecast?days=7").json() == []


def test_changing_theaters_changes_upcoming_only(
    client: TestClient, session: Session
) -> None:
    """戦域の設定を変えると次回以降の予報は変わり、今回は変わらない."""
    _make_open_room(session, "southeast_asia_jungle", 0.6)
    _deactivate(session, "southeast_asia_jungle")

    body = client.get("/api/theaters/forecast?days=3").json()

    assert [item["theater_id"] for item in body] == [
        "southeast_asia_jungle",
        "solomon",
        "solomon",
    ]
    assert body[0]["minovsky_density"] == 0.6


# --- 予報と実際のバトルの一致 ---


def _make_unit(name: str, side: str) -> MobileSuit:
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[Weapon(id="w1", name="Beam Rifle", power=100, range=500, accuracy=80)],
        side=side,
    )


def _battle_result_of(
    session: Session, room: BattleRoom, monkeypatch: pytest.MonkeyPatch
) -> BattleResult:
    """ルームで定期バトルを1回処理し、プレイヤーのバトル結果を返す."""
    suit = _make_unit("Hero", "PLAYER")
    snapshot = suit.model_dump(mode="json")
    room.status = "WAITING"
    session.add(room)
    session.add(suit)
    session.commit()
    session.add(
        BattleEntry(
            user_id=USER_ID,
            room_id=room.id,
            mobile_suit_id=suit.id,
            mobile_suit_snapshot=snapshot,
        )
    )
    session.add(
        BattleEntry(
            room_id=room.id,
            mobile_suit_id=suit.id,
            mobile_suit_snapshot=_make_unit("NPC", "ENEMY").model_dump(mode="json"),
            is_npc=True,
        )
    )
    session.commit()

    simulator = MagicMock()
    simulator.units = [snapshot_to_mobile_suit(dict(snapshot))]
    simulator.logs = []
    simulator.obstacles = []
    simulator.map_bounds = (0.0, 1000.0)
    simulator.elapsed_time = 0.1
    monkeypatch.setattr(
        run_batch,
        "run_battle",
        lambda player_unit, enemy_units, conditions=None, max_steps=0: BattleOutcome(
            simulator, player_win=True, kills=0, steps_used=1
        ),
    )
    run_batch._process_room(session, room)

    room.status = "COMPLETED"
    session.add(room)
    session.commit()
    return session.exec(
        select(BattleResult)
        .where(BattleResult.room_id == room.id)
        .where(BattleResult.user_id == USER_ID)
    ).one()


def test_forecast_matches_actual_battles(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """今回と次回の予報の戦域・濃度が、実際に開催したバトルの値と一致する."""
    room, _ = BattleRoomService.get_or_create_open_room(
        session, now=datetime(2026, 10, 1, 3, 0, tzinfo=UTC)
    )
    forecasts = TheaterForecastService.forecast(session, 2)

    current_result = _battle_result_of(session, room, monkeypatch)
    next_room, created = BattleRoomService.get_or_create_open_room(
        session, now=CURRENT_AT
    )
    assert created
    next_result = _battle_result_of(session, next_room, monkeypatch)

    for forecast, result in zip(forecasts, (current_result, next_result), strict=True):
        assert result.theater_id == forecast.theater_id
        assert result.environment == forecast.environment_id
        assert result.minovsky_density == forecast.minovsky_density
    assert forecasts[0].theater_id != forecasts[1].theater_id
