"""ランキングAPIルーター."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models.models import Leaderboard, MobileSuit, Pilot
from app.services.ranking_service import RankingService

router = APIRouter(prefix="/api/rankings", tags=["rankings"])


class LeaderboardEntry(BaseModel):
    """ランキングエントリー（レスポンス用）."""

    rank: int
    user_id: str
    pilot_name: str
    wins: int
    losses: int
    kills: int
    credits_earned: int


class PlayerProfile(BaseModel):
    """プレイヤープロフィール（公開情報のみ）."""

    pilot_name: str
    level: int
    wins: int
    losses: int
    kills: int
    mobile_suit: MobileSuit | None
    skills: dict[str, int]


@router.get("/current", response_model=list[LeaderboardEntry])
async def get_current_rankings(
    session: Session = Depends(get_session),
    limit: int = 100,
) -> list[LeaderboardEntry]:
    """現在のシーズンのランキングTop 100を取得する.

    Args:
        session: データベースセッション
        limit: 取得する順位の上限（デフォルト: 100）

    Returns:
        list[LeaderboardEntry]: ランキングエントリーのリスト
    """
    ranking_service = RankingService(session)
    rankings = ranking_service.get_current_rankings(limit=limit)

    # ランクを付与
    entries = []
    for rank, leaderboard in enumerate(rankings, start=1):
        entries.append(
            LeaderboardEntry(
                rank=rank,
                user_id=leaderboard.user_id,
                pilot_name=leaderboard.pilot_name,
                wins=leaderboard.wins,
                losses=leaderboard.losses,
                kills=leaderboard.kills,
                credits_earned=leaderboard.credits_earned,
            )
        )

    return entries


@router.get("/pilot/{user_id}/profile", response_model=PlayerProfile)
async def get_pilot_profile(
    user_id: str,
    session: Session = Depends(get_session),
) -> PlayerProfile:
    """指定したパイロットの公開プロフィール情報を取得する.

    個人情報（メールアドレス、所持クレジット等）は含まない。

    Args:
        user_id: ユーザーID (Clerk User ID)
        session: データベースセッション

    Returns:
        PlayerProfile: プレイヤープロフィール

    Raises:
        HTTPException: パイロットが見つからない場合
    """
    # パイロット情報を取得
    pilot_statement = select(Pilot).where(Pilot.user_id == user_id)
    pilot = session.exec(pilot_statement).first()

    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")

    # ランキング情報を取得
    ranking_service = RankingService(session)
    season = ranking_service.get_or_create_current_season()

    leaderboard_statement = (
        select(Leaderboard)
        .where(Leaderboard.season_id == season.id)
        .where(Leaderboard.user_id == user_id)
    )
    leaderboard = session.exec(leaderboard_statement).first()

    wins = leaderboard.wins if leaderboard else 0
    losses = leaderboard.losses if leaderboard else 0
    kills = leaderboard.kills if leaderboard else 0

    # 現在の機体を取得（最初の機体を返す）
    mobile_suit_statement = (
        select(MobileSuit).where(MobileSuit.user_id == user_id).limit(1)
    )
    mobile_suit = session.exec(mobile_suit_statement).first()

    return PlayerProfile(
        pilot_name=pilot.name,
        level=pilot.level,
        wins=wins,
        losses=losses,
        kills=kills,
        mobile_suit=mobile_suit,
        skills=pilot.skills,
    )
