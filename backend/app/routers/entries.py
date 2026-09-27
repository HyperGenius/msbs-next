# backend/app/routers/entries.py
"""エントリー関連のAPIエンドポイント."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import BattleEntry, BattleRoom, MobileSuit
from app.services.battle_room_service import BattleRoomService
from app.services.mobile_suit_service import MobileSuitService
from app.services.weapon_service import WeaponService

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


def ensure_utc_timezone(dt: datetime) -> datetime:
    """Ensure datetime has UTC timezone info.

    Args:
        dt: datetime object that may or may not have timezone info

    Returns:
        datetime object with UTC timezone info
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


# --- API Endpoints ---


@router.post("", response_model=EntryResponse)
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

    # ルームの新規作成は commit を伴う。機体の変更を巻き込まないよう、先に取得する。
    room, _ = BattleRoomService.get_or_create_open_room(session)

    # 装備中の武器改造差分（PlayerWeapon.custom_stats）をバトル開始前に反映する
    # （再装備なしでも改造結果がバトルエンジンに渡るようにするため。Issue #411）
    # ここでは commit しない。以降の mobile_suit_snapshot（model_dump）に
    # in-memory の状態を反映させれば十分で、永続化は既存エントリー作成/更新の
    # commit にまとめて含める（余計なトランザクションを増やさないため）。
    WeaponService.resync_mobile_suit_weapons(session, mobile_suit)
    session.add(mobile_suit)

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
        existing_entry.mobile_suit_snapshot = MobileSuitService.build_entry_snapshot(
            session, mobile_suit
        )
        session.add(existing_entry)
        session.commit()
        session.refresh(existing_entry)

        # Ensure scheduled_at has timezone info (UTC) before serializing
        scheduled_at = ensure_utc_timezone(room.scheduled_at)

        return EntryResponse(
            id=str(existing_entry.id),
            room_id=str(existing_entry.room_id),
            mobile_suit_id=str(existing_entry.mobile_suit_id),
            scheduled_at=scheduled_at.isoformat(),
            created_at=existing_entry.created_at.isoformat(),
        )

    # 新規エントリーを作成
    # 機体データをスナップショットとして保存
    snapshot = MobileSuitService.build_entry_snapshot(session, mobile_suit)

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
    scheduled_at = ensure_utc_timezone(room.scheduled_at)

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
    room, _ = BattleRoomService.get_or_create_open_room(session)

    # 自分のエントリーをチェック
    entry_statement = (
        select(BattleEntry)
        .where(BattleEntry.user_id == user_id)
        .where(BattleEntry.room_id == room.id)
    )
    entry = session.exec(entry_statement).first()

    if entry:
        # Ensure scheduled_at has timezone info (UTC) before serializing
        scheduled_at = ensure_utc_timezone(room.scheduled_at)

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
    scheduled_at = ensure_utc_timezone(room.scheduled_at)

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


@router.delete("")
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
