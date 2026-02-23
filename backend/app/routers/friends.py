# backend/app/routers/friends.py
"""フレンド関連のAPIエンドポイント."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, or_, select

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import Friendship, Pilot

router = APIRouter(prefix="/api/friends", tags=["friends"])


# --- Request / Response Models ---


class FriendRequestBody(BaseModel):
    """フレンドリクエスト送信ボディ."""

    friend_user_id: str


class FriendResponse(BaseModel):
    """フレンド情報レスポンス."""

    id: str
    user_id: str
    friend_user_id: str
    status: str
    pilot_name: str | None = None
    created_at: str


# --- Helper ---


def _resolve_pilot_name(session: Session, user_id: str) -> str | None:
    """Clerk User ID からパイロット名を引く."""
    pilot = session.exec(select(Pilot).where(Pilot.user_id == user_id)).first()
    return pilot.name if pilot else None


def _to_friend_response(
    session: Session, f: Friendship, my_user_id: str
) -> FriendResponse:
    """Friendship レコードをレスポンスに変換する."""
    # 相手側のユーザーIDを特定
    other_user_id = f.friend_user_id if f.user_id == my_user_id else f.user_id
    return FriendResponse(
        id=str(f.id),
        user_id=f.user_id,
        friend_user_id=f.friend_user_id,
        status=f.status,
        pilot_name=_resolve_pilot_name(session, other_user_id),
        created_at=f.created_at.isoformat(),
    )


# --- Endpoints ---


@router.post("/request", response_model=FriendResponse)
async def send_friend_request(
    body: FriendRequestBody,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> FriendResponse:
    """フレンドリクエストを送信する."""
    if body.friend_user_id == user_id:
        raise HTTPException(status_code=400, detail="自分自身にはリクエストできません")

    # 既存のリレーションをチェック（双方向）
    existing = session.exec(
        select(Friendship).where(
            or_(
                (Friendship.user_id == user_id)
                & (Friendship.friend_user_id == body.friend_user_id),
                (Friendship.user_id == body.friend_user_id)
                & (Friendship.friend_user_id == user_id),
            )
        )
    ).first()

    if existing:
        if existing.status == "ACCEPTED":
            raise HTTPException(status_code=400, detail="既にフレンドです")
        if existing.status == "PENDING":
            raise HTTPException(status_code=400, detail="リクエストは送信済みです")
        if existing.status == "BLOCKED":
            raise HTTPException(status_code=400, detail="リクエストを送信できません")

    friendship = Friendship(user_id=user_id, friend_user_id=body.friend_user_id)
    session.add(friendship)
    session.commit()
    session.refresh(friendship)

    return _to_friend_response(session, friendship, user_id)


@router.post("/accept", response_model=FriendResponse)
async def accept_friend_request(
    body: FriendRequestBody,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> FriendResponse:
    """フレンドリクエストを承認する."""
    friendship = session.exec(
        select(Friendship).where(
            Friendship.user_id == body.friend_user_id,
            Friendship.friend_user_id == user_id,
            Friendship.status == "PENDING",
        )
    ).first()

    if not friendship:
        raise HTTPException(status_code=404, detail="リクエストが見つかりません")

    friendship.status = "ACCEPTED"
    friendship.updated_at = datetime.now(UTC)
    session.add(friendship)
    session.commit()
    session.refresh(friendship)

    return _to_friend_response(session, friendship, user_id)


@router.post("/reject")
async def reject_friend_request(
    body: FriendRequestBody,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> dict[str, str]:
    """フレンドリクエストを拒否する."""
    friendship = session.exec(
        select(Friendship).where(
            Friendship.user_id == body.friend_user_id,
            Friendship.friend_user_id == user_id,
            Friendship.status == "PENDING",
        )
    ).first()

    if not friendship:
        raise HTTPException(status_code=404, detail="リクエストが見つかりません")

    session.delete(friendship)
    session.commit()

    return {"message": "リクエストを拒否しました"}


@router.delete("/{friend_user_id}")
async def remove_friend(
    friend_user_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> dict[str, str]:
    """フレンドを解除する."""
    friendship = session.exec(
        select(Friendship).where(
            Friendship.status == "ACCEPTED",
            or_(
                (Friendship.user_id == user_id)
                & (Friendship.friend_user_id == friend_user_id),
                (Friendship.user_id == friend_user_id)
                & (Friendship.friend_user_id == user_id),
            ),
        )
    ).first()

    if not friendship:
        raise HTTPException(status_code=404, detail="フレンド関係が見つかりません")

    session.delete(friendship)
    session.commit()

    return {"message": "フレンドを解除しました"}


@router.get("/", response_model=list[FriendResponse])
async def list_friends(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> list[FriendResponse]:
    """フレンド一覧を取得する（ACCEPTED のみ）."""
    friends = session.exec(
        select(Friendship).where(
            Friendship.status == "ACCEPTED",
            or_(
                Friendship.user_id == user_id,
                Friendship.friend_user_id == user_id,
            ),
        )
    ).all()

    return [_to_friend_response(session, f, user_id) for f in friends]


@router.get("/requests", response_model=list[FriendResponse])
async def list_pending_requests(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> list[FriendResponse]:
    """受信中のフレンドリクエスト一覧を取得する."""
    requests = session.exec(
        select(Friendship).where(
            Friendship.friend_user_id == user_id,
            Friendship.status == "PENDING",
        )
    ).all()

    return [_to_friend_response(session, f, user_id) for f in requests]
