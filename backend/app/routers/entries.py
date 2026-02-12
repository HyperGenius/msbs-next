# backend/app/routers/entries.py
"""エントリー関連のAPIエンドポイント."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import BattleEntry, BattleRoom, MobileSuit

router = APIRouter(prefix="/api/entries", tags=["entries"])


# --- Response Models ---


class EntryResponse(BaseModel):
    """エントリーレスポンス."""

    id: str
    room_id: str
    mobile_suit_id: str
    scheduled_at: str
    created_at: str


class EntryStatusResponse(BaseModel):
    """エントリー状況レスポンス."""

    is_entered: bool
    entry: EntryResponse | None = None
    next_room: dict | None = None


class EntryRequest(BaseModel):
    """エントリーリクエスト."""

    mobile_suit_id: str


# --- Helper Functions ---


def get_or_create_open_room(session: Session) -> BattleRoom:
    """現在募集中のルームを取得、なければ作成する."""
    # 既存のOPENなルームを探す
    statement = select(BattleRoom).where(BattleRoom.status == "OPEN")
    existing_room = session.exec(statement).first()

    if existing_room:
        return existing_room

    # なければ新しいルームを作成
    # 次の21:00 JST (= 12:00 UTC) を予定時刻とする
    # ※ JST = UTC+9 なので、21:00 JST = 12:00 UTC
    now = datetime.now(UTC)
    scheduled_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if now.hour >= 12:  # すでに12時(UTC)を過ぎていたら翌日
        scheduled_time += timedelta(days=1)

    new_room = BattleRoom(
        status="OPEN",
        scheduled_at=scheduled_time,
    )
    session.add(new_room)
    session.commit()
    session.refresh(new_room)

    return new_room


# --- API Endpoints ---


@router.post("/", response_model=EntryResponse)
async def create_entry(
    entry_request: EntryRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> EntryResponse:
    """現在募集中のルームにエントリーする."""
    # 機体が存在するか確認
    try:
        mobile_suit_uuid = UUID(entry_request.mobile_suit_id)
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail="Invalid mobile_suit_id format"
        ) from e

    mobile_suit = session.get(MobileSuit, mobile_suit_uuid)
    if not mobile_suit:
        raise HTTPException(status_code=404, detail="Mobile Suit not found")

    # 現在募集中のルームを取得または作成
    room = get_or_create_open_room(session)

    # 既存のエントリーをチェック（同じルームに既にエントリー済みか）
    existing_entry_statement = (
        select(BattleEntry)
        .where(BattleEntry.user_id == user_id)
        .where(BattleEntry.room_id == room.id)
    )
    existing_entry = session.exec(existing_entry_statement).first()

    if existing_entry:
        # 既にエントリー済みの場合は上書き
        existing_entry.mobile_suit_id = mobile_suit_uuid
        existing_entry.mobile_suit_snapshot = mobile_suit.model_dump()
        session.add(existing_entry)
        session.commit()
        session.refresh(existing_entry)

        # Ensure scheduled_at has timezone info (UTC) before serializing
        scheduled_at = room.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=UTC)

        return EntryResponse(
            id=str(existing_entry.id),
            room_id=str(existing_entry.room_id),
            mobile_suit_id=str(existing_entry.mobile_suit_id),
            scheduled_at=scheduled_at.isoformat(),
            created_at=existing_entry.created_at.isoformat(),
        )

    # 新規エントリーを作成
    # 機体データをスナップショットとして保存
    snapshot = mobile_suit.model_dump()

    new_entry = BattleEntry(
        user_id=user_id,
        room_id=room.id,
        mobile_suit_id=mobile_suit_uuid,
        mobile_suit_snapshot=snapshot,
    )
    session.add(new_entry)
    session.commit()
    session.refresh(new_entry)

    # Ensure scheduled_at has timezone info (UTC) before serializing
    scheduled_at = room.scheduled_at
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=UTC)

    return EntryResponse(
        id=str(new_entry.id),
        room_id=str(new_entry.room_id),
        mobile_suit_id=str(new_entry.mobile_suit_id),
        scheduled_at=scheduled_at.isoformat(),
        created_at=new_entry.created_at.isoformat(),
    )


@router.get("/status", response_model=EntryStatusResponse)
async def get_entry_status(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> EntryStatusResponse:
    """自分のエントリー状況を確認する."""
    # 現在募集中のルームを取得または作成
    room = get_or_create_open_room(session)

    # 自分のエントリーをチェック
    entry_statement = (
        select(BattleEntry)
        .where(BattleEntry.user_id == user_id)
        .where(BattleEntry.room_id == room.id)
    )
    entry = session.exec(entry_statement).first()

    if entry:
        # Ensure scheduled_at has timezone info (UTC) before serializing
        scheduled_at = room.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=UTC)

        return EntryStatusResponse(
            is_entered=True,
            entry=EntryResponse(
                id=str(entry.id),
                room_id=str(entry.room_id),
                mobile_suit_id=str(entry.mobile_suit_id),
                scheduled_at=scheduled_at.isoformat(),
                created_at=entry.created_at.isoformat(),
            ),
            next_room={
                "id": str(room.id),
                "status": room.status,
                "scheduled_at": scheduled_at.isoformat(),
            },
        )

    # エントリーしていない
    # Ensure scheduled_at has timezone info (UTC) before serializing
    scheduled_at = room.scheduled_at
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=UTC)

    return EntryStatusResponse(
        is_entered=False,
        entry=None,
        next_room={
            "id": str(room.id),
            "status": room.status,
            "scheduled_at": scheduled_at.isoformat(),
        },
    )


@router.get("/count")
async def get_entry_count(
    session: Session = Depends(get_session),
) -> dict[str, int]:
    """現在募集中のルームへのエントリー数を取得する."""
    # 現在募集中のルームを取得
    room_statement = select(BattleRoom).where(BattleRoom.status == "OPEN")
    room = session.exec(room_statement).first()

    if not room:
        return {"count": 0}

    # このルームへのエントリー数をカウント
    entry_statement = select(BattleEntry).where(BattleEntry.room_id == room.id)
    entries = session.exec(entry_statement).all()

    return {"count": len(entries)}


@router.delete("/")
async def cancel_entry(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> dict[str, str]:
    """エントリーをキャンセルする."""
    # 現在募集中のルームを取得
    room_statement = select(BattleRoom).where(BattleRoom.status == "OPEN")
    room = session.exec(room_statement).first()

    if not room:
        raise HTTPException(status_code=404, detail="No open room found")

    # 自分のエントリーを削除
    entry_statement = (
        select(BattleEntry)
        .where(BattleEntry.user_id == user_id)
        .where(BattleEntry.room_id == room.id)
    )
    entry = session.exec(entry_statement).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    session.delete(entry)
    session.commit()

    return {"message": "Entry cancelled successfully"}
