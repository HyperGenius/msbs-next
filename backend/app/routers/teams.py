# backend/app/routers/teams.py
"""チーム関連のAPIエンドポイント."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.auth import get_current_user
from app.db import get_session
from app.models.models import (
    BattleEntry,
    BattleRoom,
    MobileSuit,
    Team,
    TeamMember,
)

router = APIRouter(prefix="/api/teams", tags=["teams"])

MAX_TEAM_SIZE = 3


# --- Request / Response Models ---


class TeamCreateRequest(BaseModel):
    """チーム作成リクエスト."""

    name: str


class TeamInviteRequest(BaseModel):
    """チーム招待リクエスト."""

    user_id: str


class TeamMemberResponse(BaseModel):
    """チームメンバーレスポンス."""

    user_id: str
    is_ready: bool
    joined_at: str


class TeamResponse(BaseModel):
    """チーム情報レスポンス."""

    id: str
    owner_user_id: str
    name: str
    status: str
    members: list[TeamMemberResponse]
    created_at: str


class TeamEntryRequest(BaseModel):
    """チームエントリーリクエスト."""

    team_id: str
    mobile_suit_id: str


# --- Helper ---


def _team_response(team: Team, members: list[TeamMember]) -> TeamResponse:
    return TeamResponse(
        id=str(team.id),
        owner_user_id=team.owner_user_id,
        name=team.name,
        status=team.status,
        members=[
            TeamMemberResponse(
                user_id=m.user_id,
                is_ready=m.is_ready,
                joined_at=m.joined_at.isoformat(),
            )
            for m in members
        ],
        created_at=team.created_at.isoformat(),
    )


def _get_team_members(session: Session, team_id: object) -> list[TeamMember]:
    return list(
        session.exec(select(TeamMember).where(TeamMember.team_id == team_id)).all()
    )


# --- Endpoints ---


@router.post("/create", response_model=TeamResponse)
async def create_team(
    body: TeamCreateRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> TeamResponse:
    """チームを作成する（作成者は自動的にメンバーに追加される）."""
    # 既にアクティブなチームに所属していないかチェック
    existing_membership = session.exec(
        select(TeamMember)
        .join(Team)
        .where(TeamMember.user_id == user_id, Team.status != "DISBANDED")
    ).first()
    if existing_membership:
        raise HTTPException(
            status_code=400, detail="既にチームに所属しています。先に現在のチームを離脱してください"
        )

    team = Team(owner_user_id=user_id, name=body.name)
    session.add(team)
    session.flush()

    member = TeamMember(team_id=team.id, user_id=user_id, is_ready=False)
    session.add(member)
    session.commit()
    session.refresh(team)

    members = _get_team_members(session, team.id)
    return _team_response(team, members)


@router.post("/{team_id}/invite", response_model=TeamResponse)
async def invite_member(
    team_id: str,
    body: TeamInviteRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> TeamResponse:
    """チームにメンバーを招待する（オーナーのみ）."""
    import uuid as _uuid

    team = session.get(Team, _uuid.UUID(team_id))
    if not team or team.status == "DISBANDED":
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    if team.owner_user_id != user_id:
        raise HTTPException(status_code=403, detail="チームオーナーのみ招待できます")

    members = _get_team_members(session, team.id)
    if len(members) >= MAX_TEAM_SIZE:
        raise HTTPException(
            status_code=400, detail=f"チームの上限({MAX_TEAM_SIZE}人)に達しています"
        )

    # 既に所属していないかチェック
    if any(m.user_id == body.user_id for m in members):
        raise HTTPException(status_code=400, detail="既にチームメンバーです")

    # 別のアクティブチームに所属していないかチェック
    other_membership = session.exec(
        select(TeamMember)
        .join(Team)
        .where(TeamMember.user_id == body.user_id, Team.status != "DISBANDED")
    ).first()
    if other_membership:
        raise HTTPException(status_code=400, detail="対象プレイヤーは既に別のチームに所属しています")

    new_member = TeamMember(team_id=team.id, user_id=body.user_id, is_ready=False)
    session.add(new_member)
    session.commit()

    members = _get_team_members(session, team.id)
    return _team_response(team, members)


@router.post("/{team_id}/ready", response_model=TeamResponse)
async def set_ready(
    team_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> TeamResponse:
    """自分の準備完了状態をトグルする."""
    import uuid as _uuid

    team = session.get(Team, _uuid.UUID(team_id))
    if not team or team.status == "DISBANDED":
        raise HTTPException(status_code=404, detail="チームが見つかりません")

    member = session.exec(
        select(TeamMember).where(
            TeamMember.team_id == team.id, TeamMember.user_id == user_id
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="チームメンバーではありません")

    member.is_ready = not member.is_ready
    session.add(member)

    # 全員 Ready ならチームステータスを READY にする
    members = _get_team_members(session, team.id)
    if all(m.is_ready or m.user_id == user_id and not member.is_ready for m in members):
        # re-check after toggle
        pass
    # Re-fetch to reflect the toggle
    session.flush()
    members = _get_team_members(session, team.id)
    if len(members) >= 2 and all(m.is_ready for m in members):
        team.status = "READY"
        team.updated_at = datetime.now(UTC)
    else:
        if team.status == "READY":
            team.status = "FORMING"
            team.updated_at = datetime.now(UTC)
    session.add(team)
    session.commit()
    session.refresh(team)

    members = _get_team_members(session, team.id)
    return _team_response(team, members)


@router.delete("/{team_id}/leave")
async def leave_team(
    team_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> dict[str, str]:
    """チームから離脱する（オーナーが離脱するとチームは解散）."""
    import uuid as _uuid

    team = session.get(Team, _uuid.UUID(team_id))
    if not team or team.status == "DISBANDED":
        raise HTTPException(status_code=404, detail="チームが見つかりません")

    member = session.exec(
        select(TeamMember).where(
            TeamMember.team_id == team.id, TeamMember.user_id == user_id
        )
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="チームメンバーではありません")

    if team.owner_user_id == user_id:
        # オーナーが離脱 → チーム解散
        team.status = "DISBANDED"
        team.updated_at = datetime.now(UTC)
        session.add(team)
        # 全メンバーを削除
        all_members = _get_team_members(session, team.id)
        for m in all_members:
            session.delete(m)
        session.commit()
        return {"message": "チームを解散しました"}

    session.delete(member)
    # チームステータスをリセット
    if team.status == "READY":
        team.status = "FORMING"
        team.updated_at = datetime.now(UTC)
        session.add(team)
    session.commit()
    return {"message": "チームを離脱しました"}


@router.get("/current", response_model=TeamResponse | None)
async def get_current_team(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> TeamResponse | None:
    """現在所属しているチームを取得する."""
    membership = session.exec(
        select(TeamMember)
        .join(Team)
        .where(TeamMember.user_id == user_id, Team.status != "DISBANDED")
    ).first()

    if not membership:
        return None

    team = session.get(Team, membership.team_id)
    if not team:
        return None

    members = _get_team_members(session, team.id)
    return _team_response(team, members)


@router.post("/entry", response_model=dict)
async def team_entry(
    body: TeamEntryRequest,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> dict:
    """チーム単位でバトルにエントリーする.

    チームの全メンバーが READY 状態であることが必要。
    各メンバーの機体は個別に指定する（呼び出し元はオーナーのみ）。
    簡易実装: オーナーが自身の機体IDを指定し、他メンバーの機体は自動で選択する。
    """
    import uuid as _uuid

    team = session.get(Team, _uuid.UUID(body.team_id))
    if not team or team.status == "DISBANDED":
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    if team.owner_user_id != user_id:
        raise HTTPException(status_code=403, detail="チームオーナーのみエントリーできます")
    if team.status != "READY":
        raise HTTPException(status_code=400, detail="全メンバーの準備が完了していません")

    # 現在募集中のルームを取得
    room = session.exec(select(BattleRoom).where(BattleRoom.status == "OPEN")).first()
    if not room:
        raise HTTPException(status_code=404, detail="現在募集中のルームがありません")

    members = _get_team_members(session, team.id)
    entries_created = []

    for member in members:
        # 既存エントリーをチェック
        existing = session.exec(
            select(BattleEntry).where(
                BattleEntry.user_id == member.user_id,
                BattleEntry.room_id == room.id,
            )
        ).first()
        if existing:
            entries_created.append(str(existing.id))
            continue

        # メンバーの機体を取得（オーナーは指定された機体、他は最初の機体を使用）
        if member.user_id == user_id:
            ms = session.get(MobileSuit, _uuid.UUID(body.mobile_suit_id))
        else:
            ms = session.exec(
                select(MobileSuit).where(
                    MobileSuit.user_id == member.user_id,
                    MobileSuit.side == "PLAYER",
                )
            ).first()

        if not ms:
            raise HTTPException(
                status_code=400,
                detail=f"メンバー {member.user_id} の機体が見つかりません",
            )

        entry = BattleEntry(
            user_id=member.user_id,
            room_id=room.id,
            mobile_suit_id=ms.id,
            mobile_suit_snapshot=ms.model_dump(),
        )
        session.add(entry)
        session.flush()
        entries_created.append(str(entry.id))

    session.commit()

    return {
        "message": f"チーム「{team.name}」でエントリーしました（{len(entries_created)}名）",
        "entry_ids": entries_created,
        "room_id": str(room.id),
    }
