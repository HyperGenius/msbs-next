"""ランキング集計サービス."""

from datetime import UTC, datetime

from sqlalchemy import case
from sqlmodel import Session, func, select

from app.models.models import BattleResult, Leaderboard, Pilot, Season


class RankingService:
    """ランキング集計サービス."""

    def __init__(self, session: Session) -> None:
        """初期化.

        Args:
            session: データベースセッション
        """
        self.session = session

    def get_or_create_current_season(self) -> Season:
        """現在のアクティブシーズンを取得または作成する.

        Returns:
            Season: 現在のシーズン
        """
        # アクティブなシーズンを取得
        statement = select(Season).where(Season.is_active == True)  # noqa: E712
        season = self.session.exec(statement).first()

        if season:
            return season

        # シーズンが存在しない場合は作成
        season = Season(
            name="プレシーズン",
            start_date=datetime.now(UTC),
            is_active=True,
        )
        self.session.add(season)
        self.session.commit()
        self.session.refresh(season)

        return season

    def calculate_ranking(self) -> None:
        """バトル結果から現在のシーズンのランキングを集計・更新する."""
        season = self.get_or_create_current_season()

        # 全ユーザーのバトル結果を集計
        # user_idがNoneでないBattleResultのみを対象とする
        statement = (
            select(
                BattleResult.user_id,
                func.count().label("total_battles"),
                func.sum(
                    case((BattleResult.win_loss == "WIN", 1), else_=0)  # type: ignore[arg-type]
                ).label("wins"),
                func.sum(
                    case((BattleResult.win_loss == "LOSE", 1), else_=0)  # type: ignore[arg-type]
                ).label("losses"),
            )
            .where(BattleResult.user_id != None)  # type: ignore[union-attr]  # noqa: E711
            .group_by(BattleResult.user_id)
        )

        results = self.session.exec(statement).all()

        for row in results:
            user_id = row[0]
            wins = row[2] or 0
            losses = row[3] or 0

            # user_idがNoneの場合はスキップ（型チェック対策）
            if user_id is None:
                continue

            # Pilotからパイロット名を取得
            pilot_statement = select(Pilot).where(Pilot.user_id == user_id)
            pilot = self.session.exec(pilot_statement).first()

            if not pilot:
                continue

            # 撃墜数と獲得クレジットを集計
            # BattleLogから撃墜数をカウントするのは複雑なので、
            # 簡易的に勝利数から推定（1勝あたり平均撃墜数を仮定）
            # または別途集計ロジックを実装する必要がある
            kills = self._calculate_kills_for_user(user_id)
            credits_earned = self._calculate_credits_for_user(user_id)

            # Leaderboardレコードを更新または作成（Upsert）
            leaderboard_statement = (
                select(Leaderboard)
                .where(Leaderboard.season_id == season.id)
                .where(Leaderboard.user_id == user_id)
            )
            leaderboard = self.session.exec(leaderboard_statement).first()

            if leaderboard:
                # 既存レコードを更新
                leaderboard.pilot_name = pilot.name
                leaderboard.wins = wins
                leaderboard.losses = losses
                leaderboard.kills = kills
                leaderboard.credits_earned = credits_earned
                leaderboard.updated_at = datetime.now(UTC)
            else:
                # 新規レコードを作成
                leaderboard = Leaderboard(
                    season_id=season.id,
                    user_id=user_id,
                    pilot_name=pilot.name,
                    wins=wins,
                    losses=losses,
                    kills=kills,
                    credits_earned=credits_earned,
                )
                self.session.add(leaderboard)

        self.session.commit()

    def _calculate_kills_for_user(self, user_id: str) -> int:
        """特定ユーザーの撃墜数を計算する.

        Note: BattleLogには撃墜情報が含まれているが、
        ログをパースするのは重いため、簡易的に勝利数×平均撃墜数で推定する。
        将来的にはBattleResultに撃墜数フィールドを追加すべき。

        Args:
            user_id: ユーザーID

        Returns:
            int: 推定撃墜数
        """
        # 勝利時の平均撃墜数を2機と仮定
        statement = (
            select(func.count())
            .select_from(BattleResult)
            .where(BattleResult.user_id == user_id)
            .where(BattleResult.win_loss == "WIN")
        )
        wins = self.session.exec(statement).first() or 0
        return wins * 2  # 1勝あたり平均2機撃墜と仮定

    def _calculate_credits_for_user(self, user_id: str) -> int:
        """特定ユーザーの獲得クレジットを計算する.

        Note: 現在の実装では、報酬はPilotテーブルに直接加算されており、
        バトルごとの獲得クレジットの履歴は保持されていない。
        簡易的に勝利数と撃墜数から推定する。

        Args:
            user_id: ユーザーID

        Returns:
            int: 推定獲得クレジット
        """
        # 勝利数を取得
        statement = (
            select(func.count())
            .select_from(BattleResult)
            .where(BattleResult.user_id == user_id)
            .where(BattleResult.win_loss == "WIN")
        )
        wins = self.session.exec(statement).first() or 0

        # 簡易計算: 勝利ごとに50クレジット、撃墜ごとに50クレジットと仮定
        kills = self._calculate_kills_for_user(user_id)
        return (wins * 50) + (kills * 50)

    def get_current_rankings(self, limit: int = 100) -> list[Leaderboard]:
        """現在のシーズンのランキングを取得する.

        Args:
            limit: 取得する順位の上限（デフォルト: 100）

        Returns:
            list[Leaderboard]: ランキングデータのリスト
        """
        season = self.get_or_create_current_season()

        from sqlalchemy import desc

        statement = (
            select(Leaderboard)
            .where(Leaderboard.season_id == season.id)
            .order_by(
                desc(Leaderboard.wins),  # type: ignore[arg-type]
                desc(Leaderboard.kills),  # type: ignore[arg-type]
            )
            .limit(limit)
        )

        rankings = self.session.exec(statement).all()
        return list(rankings)
