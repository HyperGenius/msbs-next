"""戦域ローテーションとルームへの割り当てのテスト."""

from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, select

from app.models.models import BattleRoom, MasterTheater
from app.services.battle_room_service import BattleRoomService
from app.services.matching_service import MatchingService
from app.services.theater_service import (
    THEATER_ROTATION_EPOCH,
    TheaterService,
)


def _activate_jungle(session: Session) -> None:
    """東南アジア密林をローテーションに含める."""
    jungle = session.get(MasterTheater, "southeast_asia_jungle")
    assert jungle is not None
    jungle.is_active = True
    session.add(jungle)
    session.commit()


def _make_theater(
    theater_id: str, base_minovsky: float, minovsky_variance: float
) -> MasterTheater:
    """DB に保存しない戦域を作る."""
    return MasterTheater(
        id=theater_id,
        name=theater_id,
        environment_id="SPACE",
        base_minovsky=base_minovsky,
        minovsky_variance=minovsky_variance,
    )


# --- 開催日 ---


def test_battle_date_uses_jst() -> None:
    """開催日は JST の日付になる."""
    assert TheaterService.battle_date_of(
        datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
    ) == date(2026, 9, 27)
    # 15:00 UTC は JST の翌日 0:00。
    assert TheaterService.battle_date_of(
        datetime(2026, 9, 27, 15, 0, tzinfo=UTC)
    ) == date(2026, 9, 28)


def test_battle_date_treats_naive_datetime_as_utc() -> None:
    """タイムゾーン無しの時刻は UTC として扱う."""
    assert TheaterService.battle_date_of(datetime(2026, 9, 27, 15, 0)) == date(
        2026, 9, 28
    )


# --- ミノフスキー濃度 ---


def test_minovsky_is_deterministic_and_within_variance() -> None:
    """濃度は開催日と戦域で決まり、基準値 ± 揺らぎ幅に収まる."""
    theater = _make_theater("test", base_minovsky=0.5, minovsky_variance=0.2)
    for offset in range(30):
        battle_date = date(2026, 10, 1) + timedelta(days=offset)
        value = TheaterService.roll_minovsky(battle_date, theater)
        assert value == TheaterService.roll_minovsky(battle_date, theater)
        assert 0.3 <= value <= 0.7
        assert value == round(value, 2)


def test_minovsky_varies_by_date() -> None:
    """揺らぎ幅があれば開催日ごとに濃度が変わる."""
    theater = _make_theater("test", base_minovsky=0.5, minovsky_variance=0.2)
    values = {
        TheaterService.roll_minovsky(date(2026, 10, 1) + timedelta(days=i), theater)
        for i in range(10)
    }
    assert len(values) > 1


def test_minovsky_is_clamped_to_unit_range() -> None:
    """濃度は 0〜1 に収まる."""
    high = _make_theater("high", base_minovsky=0.9, minovsky_variance=0.5)
    low = _make_theater("low", base_minovsky=0.1, minovsky_variance=0.5)
    for offset in range(50):
        battle_date = date(2026, 10, 1) + timedelta(days=offset)
        assert 0.0 <= TheaterService.roll_minovsky(battle_date, high) <= 1.0
        assert 0.0 <= TheaterService.roll_minovsky(battle_date, low) <= 1.0


def test_minovsky_is_zero_without_variance() -> None:
    """基準値 0・揺らぎ 0 なら濃度は 0."""
    theater = _make_theater("test", base_minovsky=0.0, minovsky_variance=0.0)
    assert TheaterService.roll_minovsky(date(2026, 10, 1), theater) == 0.0


# --- 戦域の決定 ---


def test_resolve_for_date_is_deterministic(session: Session) -> None:
    """同じ開催日なら何度計算しても同じ結果になる."""
    _activate_jungle(session)
    battle_date = date(2026, 10, 1)
    first = TheaterService.resolve_for_date(session, battle_date)
    second = TheaterService.resolve_for_date(session, battle_date)
    assert first == second


def test_initial_data_alternates_space_and_forest(session: Session) -> None:
    """初期データではソロモン宙域と東南アジア密林が日替わりで交互になる."""
    assignments = TheaterService.forecast(session, THEATER_ROTATION_EPOCH, 30)
    for offset, assignment in enumerate(assignments):
        if offset % 2 == 0:
            assert assignment.theater_id == "solomon"
            assert assignment.environment_id == "SPACE"
            assert 0.2 <= assignment.minovsky_density <= 0.5
        else:
            assert assignment.theater_id == "southeast_asia_jungle"
            assert assignment.environment_id == "FOREST"
            assert 0.45 <= assignment.minovsky_density <= 0.75


def test_active_theaters_alternate_by_date(session: Session) -> None:
    """有効な戦域が複数あると開催日ごとに切り替わる."""
    _activate_jungle(session)
    assignments = TheaterService.forecast(session, THEATER_ROTATION_EPOCH, 4)
    assert [a.theater_id for a in assignments] == [
        "solomon",
        "southeast_asia_jungle",
        "solomon",
        "southeast_asia_jungle",
    ]
    assert assignments[1].environment_id == "FOREST"


def test_rotation_follows_rotation_order(session: Session) -> None:
    """ローテーションは rotation_order の昇順に並ぶ."""
    _activate_jungle(session)
    jungle = session.get(MasterTheater, "southeast_asia_jungle")
    assert jungle is not None
    jungle.rotation_order = 0
    session.add(jungle)
    session.commit()

    assignment = TheaterService.resolve_for_date(session, THEATER_ROTATION_EPOCH)
    assert assignment.theater_id == "southeast_asia_jungle"


def test_no_active_theater_returns_empty_assignment(session: Session) -> None:
    """有効な戦域が無ければ戦域なし・濃度 0 になる."""
    for theater in session.exec(select(MasterTheater)).all():
        theater.is_active = False
        session.add(theater)
    session.commit()

    assignment = TheaterService.resolve_for_date(session, date(2026, 10, 1))
    assert assignment.theater_id is None
    assert assignment.environment_id is None
    assert assignment.minovsky_density == 0.0


def test_forecast_matches_resolve_for_date(session: Session) -> None:
    """予報は各開催日の決定結果と一致する."""
    _activate_jungle(session)
    from_date = date(2026, 10, 1)
    forecast = TheaterService.forecast(session, from_date, 7)
    assert [a.battle_date for a in forecast] == [
        from_date + timedelta(days=i) for i in range(7)
    ]
    for assignment in forecast:
        assert assignment == TheaterService.resolve_for_date(
            session, assignment.battle_date
        )


# --- ルームへの割り当て ---


def _clear_rooms(session: Session) -> None:
    """全ルームを削除する."""
    for room in session.exec(select(BattleRoom)).all():
        session.delete(room)
    session.commit()


def test_next_scheduled_at() -> None:
    """開催予定時刻は次の 12:00 UTC になる."""
    before = datetime(2026, 9, 27, 11, 59, tzinfo=UTC)
    at = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
    assert BattleRoomService.next_scheduled_at(before) == at
    assert BattleRoomService.next_scheduled_at(at) == at + timedelta(days=1)


def test_created_room_has_theater_of_battle_date(session: Session) -> None:
    """作成したルームに開催日の戦域と濃度が入る."""
    _clear_rooms(session)
    _activate_jungle(session)
    now = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)

    room, created = BattleRoomService.get_or_create_open_room(session, now=now)

    assert created
    expected = TheaterService.resolve_for_date(session, date(2026, 10, 1))
    assert room.theater_id == expected.theater_id
    assert room.minovsky_density == expected.minovsky_density


def test_existing_open_room_keeps_its_theater(session: Session) -> None:
    """設定を変えても作成済みの OPEN ルームの戦域は変わらない."""
    _clear_rooms(session)
    now = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)
    room, _ = BattleRoomService.get_or_create_open_room(session, now=now)
    original_theater_id = room.theater_id
    assert original_theater_id is not None

    theater = session.get(MasterTheater, original_theater_id)
    assert theater is not None
    theater.is_active = False
    session.add(theater)
    session.commit()

    same_room, created = BattleRoomService.get_or_create_open_room(session, now=now)
    assert not created
    assert same_room.id == room.id
    assert same_room.theater_id == original_theater_id


def test_postponed_room_is_reassigned(session: Session) -> None:
    """延期したルームは延期後の日付で戦域を決め直す."""
    _clear_rooms(session)
    _activate_jungle(session)
    scheduled_at = (datetime.now(UTC) - timedelta(days=1)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    room = BattleRoom(status="OPEN", scheduled_at=scheduled_at)
    BattleRoomService.assign_theater(session, room)
    session.commit()
    original_theater = room.theater_id

    MatchingService(session).create_rooms()
    session.refresh(room)

    postponed_date = TheaterService.battle_date_of(scheduled_at + timedelta(days=1))
    expected = TheaterService.resolve_for_date(session, postponed_date)
    assert room.status == "OPEN"
    assert room.theater_id == expected.theater_id
    assert room.theater_id != original_theater
    assert room.minovsky_density == expected.minovsky_density
