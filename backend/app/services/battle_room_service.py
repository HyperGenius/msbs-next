"""定期バトルのルームを作成・延期するサービス."""

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, col, select

from app.models.models import BattleEntry, BattleRoom
from app.services.theater_service import TheaterService

# 21:00 JST
BATTLE_HOUR_UTC = 12


class BattleRoomService:
    """バトルルームサービス."""

    @staticmethod
    def next_scheduled_at(now: datetime) -> datetime:
        """直近の開催予定時刻を返す。now ちょうどのときは翌日にする."""
        scheduled_at = now.astimezone(UTC).replace(
            hour=BATTLE_HOUR_UTC, minute=0, second=0, microsecond=0
        )
        if now >= scheduled_at:
            scheduled_at += timedelta(days=1)
        return scheduled_at

    @staticmethod
    def find_open_room(session: Session) -> BattleRoom | None:
        """募集中のデイリーバトルロイヤルのルームを返す。作戦ルームは含めない."""
        return session.exec(
            select(BattleRoom).where(
                BattleRoom.status == "OPEN", col(BattleRoom.mission_id).is_(None)
            )
        ).first()

    @staticmethod
    def find_open_entry(
        session: Session, user_id: str
    ) -> tuple[BattleEntry, BattleRoom] | None:
        """募集中のルーム（バトルロイヤル・作戦）にあるユーザーのエントリーを返す.

        1ユーザーが1開催に出られるのはどちらか1つなので、見つかるのは最大1件。
        """
        row = session.exec(
            select(BattleEntry, BattleRoom)
            .join(BattleRoom, col(BattleEntry.room_id) == col(BattleRoom.id))
            .where(BattleEntry.user_id == user_id, BattleRoom.status == "OPEN")
            .order_by(col(BattleEntry.created_at).desc())
        ).first()
        return None if row is None else (row[0], row[1])

    @staticmethod
    def create_mission_room(
        session: Session, open_room: BattleRoom, mission_id: int
    ) -> BattleRoom:
        """作戦の専用ルームを作る。コミットは呼び出し側で行う.

        開催予定時刻・戦域・濃度は、同じ開催のバトルロイヤルのルームに合わせる。
        """
        room = BattleRoom(
            status="OPEN",
            scheduled_at=open_room.scheduled_at,
            theater_id=open_room.theater_id,
            minovsky_density=open_room.minovsky_density,
            mission_id=mission_id,
        )
        session.add(room)
        session.flush()
        return room

    @staticmethod
    def remove_entry(session: Session, entry: BattleEntry, room: BattleRoom) -> None:
        """エントリーを消す。作戦ルームは専用なので一緒に消す.

        コミットは呼び出し側で行う。
        """
        session.delete(entry)
        if room.mission_id is not None:
            session.flush()
            session.delete(room)

    @staticmethod
    def assign_theater(session: Session, room: BattleRoom) -> None:
        """開催予定時刻の日付で、ルームに戦域と濃度を割り当てる.

        開催予定時刻を変えたときも呼ぶ。コミットは呼び出し側で行う。
        """
        assignment = TheaterService.resolve_for_date(
            session, TheaterService.battle_date_of(room.scheduled_at)
        )
        room.theater_id = assignment.theater_id
        room.minovsky_density = assignment.minovsky_density
        session.add(room)

    @staticmethod
    def get_or_create_open_room(
        session: Session, now: datetime | None = None
    ) -> tuple[BattleRoom, bool]:
        """募集中のルームを返す。無ければ次の開催予定時刻で作成する.

        作成したときは commit と refresh を行う。
        セッションに未コミットの変更があると、それも一緒に commit される。

        Returns:
            ルームと、新しく作成したかどうか。
        """
        existing = BattleRoomService.find_open_room(session)
        if existing is not None:
            return existing, False

        room = BattleRoom(
            status="OPEN",
            scheduled_at=BattleRoomService.next_scheduled_at(now or datetime.now(UTC)),
        )
        BattleRoomService.assign_theater(session, room)
        session.commit()
        session.refresh(room)
        return room, True
