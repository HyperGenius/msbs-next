"""ランキング計算ロジックの挙動テスト.

conftest.py のインメモリSQLiteセッションを使い、
calculate_ranking() とランキングAPIエンドポイントの動作を検証する。
"""

from datetime import UTC, datetime

from fastapi import status
from sqlmodel import select

from app.models.models import BattleResult, Leaderboard, Pilot, Season
from app.services.ranking_service import RankingService


def test_calculate_ranking_creates_leaderboard_entries(session):
    """calculate_ranking() がバトル結果からLeaderboardレコードを作成する."""
    # パイロットを作成
    pilot = Pilot(
        user_id="user_rank_001",
        name="Amuro Ray",
        level=5,
        exp=500,
        credits=2000,
    )
    session.add(pilot)
    session.commit()

    # バトル結果を追加（3勝1敗）
    for _ in range(3):
        session.add(BattleResult(user_id="user_rank_001", win_loss="WIN"))
    session.add(BattleResult(user_id="user_rank_001", win_loss="LOSE"))
    session.commit()

    # ランキングを計算
    ranking_service = RankingService(session)
    ranking_service.calculate_ranking()

    # Leaderboardレコードが作成されたことを確認
    season = ranking_service.get_or_create_current_season()
    entry = session.exec(
        select(Leaderboard)
        .where(Leaderboard.user_id == "user_rank_001")
        .where(Leaderboard.season_id == season.id)
    ).first()

    assert entry is not None
    assert entry.pilot_name == "Amuro Ray"
    assert entry.wins == 3
    assert entry.losses == 1
    assert entry.kills > 0  # 勝利数×2の推定値
    assert entry.credits_earned > 0


def test_calculate_ranking_upserts_existing_entry(session):
    """calculate_ranking() を2回呼んでも重複しない（Upsert）."""
    pilot = Pilot(
        user_id="user_rank_002",
        name="Char Aznable",
        level=10,
        exp=1000,
        credits=5000,
    )
    session.add(pilot)
    session.commit()

    session.add(BattleResult(user_id="user_rank_002", win_loss="WIN"))
    session.commit()

    ranking_service = RankingService(session)
    ranking_service.calculate_ranking()
    ranking_service.calculate_ranking()  # 2回目

    season = ranking_service.get_or_create_current_season()
    entries = session.exec(
        select(Leaderboard)
        .where(Leaderboard.user_id == "user_rank_002")
        .where(Leaderboard.season_id == season.id)
    ).all()

    # 重複していないこと
    assert len(entries) == 1
    assert entries[0].wins == 1


def test_get_current_rankings_returns_sorted_list(session):
    """get_current_rankings() が勝利数の降順で返す."""
    for i, (name, uid, wins, losses) in enumerate(
        [
            ("Pilot A", "user_rank_a", 10, 2),
            ("Pilot B", "user_rank_b", 5, 5),
            ("Pilot C", "user_rank_c", 8, 3),
        ]
    ):
        pilot = Pilot(user_id=uid, name=name, level=1, exp=0, credits=1000)
        session.add(pilot)
        session.commit()

        for _ in range(wins):
            session.add(BattleResult(user_id=uid, win_loss="WIN"))
        for _ in range(losses):
            session.add(BattleResult(user_id=uid, win_loss="LOSE"))
        session.commit()

    ranking_service = RankingService(session)
    ranking_service.calculate_ranking()
    rankings = ranking_service.get_current_rankings()

    assert len(rankings) == 3
    # 勝利数の降順: A(10) > C(8) > B(5)
    assert rankings[0].pilot_name == "Pilot A"
    assert rankings[1].pilot_name == "Pilot C"
    assert rankings[2].pilot_name == "Pilot B"


def test_get_or_create_current_season_creates_season(session):
    """アクティブシーズンが存在しない場合、新しいシーズンを作成する."""
    ranking_service = RankingService(session)
    season = ranking_service.get_or_create_current_season()

    assert season.id is not None
    assert season.is_active is True
    assert season.name == "プレシーズン"


def test_get_or_create_current_season_reuses_existing(session):
    """既存のアクティブシーズンを再利用する."""
    existing = Season(name="Season 1", start_date=datetime.now(UTC), is_active=True)
    session.add(existing)
    session.commit()
    session.refresh(existing)

    ranking_service = RankingService(session)
    season1 = ranking_service.get_or_create_current_season()
    season2 = ranking_service.get_or_create_current_season()

    assert season1.id == season2.id == existing.id


def test_rankings_api_returns_empty_list(client):
    """ランキングデータがない場合、空のリストを返す."""
    response = client.get("/api/rankings/current")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_rankings_api_returns_ranked_entries(client, session):
    """ランキングAPIが正しくランク付きエントリーを返す."""
    pilot = Pilot(
        user_id="user_api_rank",
        name="Wing Zero",
        level=3,
        exp=300,
        credits=3000,
    )
    session.add(pilot)
    session.commit()

    for _ in range(5):
        session.add(BattleResult(user_id="user_api_rank", win_loss="WIN"))
    session.commit()

    # ランキングを計算
    ranking_service = RankingService(session)
    ranking_service.calculate_ranking()

    response = client.get("/api/rankings/current")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) == 1
    assert data[0]["rank"] == 1
    assert data[0]["pilot_name"] == "Wing Zero"
    assert data[0]["wins"] == 5
    # センシティブフィールドが含まれていないことを確認
    assert "credits" not in data[0]
    assert "email" not in data[0]


def test_pilot_profile_api_excludes_sensitive_data(client, session):
    """プレイヤープロフィールAPIがセンシティブ情報を含まない."""
    pilot = Pilot(
        user_id="user_profile_test",
        name="Heero Yuy",
        level=7,
        exp=700,
        credits=9999,  # センシティブ情報
        skills={"ACCURACY": 2},
    )
    session.add(pilot)
    session.commit()

    response = client.get("/api/rankings/pilot/user_profile_test/profile")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["pilot_name"] == "Heero Yuy"
    assert data["level"] == 7

    # センシティブフィールドが含まれていないこと
    assert "credits" not in data
    assert "email" not in data
    assert "user_id" not in data


def test_pilot_profile_api_returns_404_for_unknown_pilot(client):
    """存在しないパイロットのプロフィール取得で404が返る."""
    response = client.get("/api/rankings/pilot/unknown_user_xyz/profile")
    assert response.status_code == status.HTTP_404_NOT_FOUND
