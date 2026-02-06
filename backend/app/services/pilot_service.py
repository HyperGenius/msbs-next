"""パイロット関連のビジネスロジック."""

from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.models import Pilot


class PilotService:
    """パイロット成長・報酬管理サービス."""

    def __init__(self, session: Session):
        """サービスを初期化する.

        Args:
            session: データベースセッション
        """
        self.session = session

    @staticmethod
    def calculate_required_exp(level: int) -> int:
        """次のレベルに必要な経験値を計算する.

        Args:
            level: 現在のレベル

        Returns:
            次のレベルに必要な経験値
        """
        return level * 100

    def get_or_create_pilot(self, user_id: str, name: str) -> Pilot:
        """パイロットを取得または作成する.

        Args:
            user_id: Clerk User ID
            name: パイロット名

        Returns:
            Pilot: パイロットデータ
        """
        statement = select(Pilot).where(Pilot.user_id == user_id)
        pilot = self.session.exec(statement).first()

        if not pilot:
            pilot = Pilot(
                user_id=user_id,
                name=name,
                level=1,
                exp=0,
                credits=1000,
            )
            self.session.add(pilot)
            self.session.commit()
            self.session.refresh(pilot)

        return pilot

    def add_rewards(
        self,
        pilot: Pilot,
        exp_gained: int,
        credits_gained: int,
    ) -> tuple[Pilot, list[str]]:
        """報酬を付与してレベルアップ処理を行う.

        Args:
            pilot: 対象パイロット
            exp_gained: 獲得経験値
            credits_gained: 獲得クレジット

        Returns:
            tuple[Pilot, list[str]]: 更新後のパイロットとログメッセージのリスト
        """
        logs = []

        # 報酬を付与
        pilot.exp += exp_gained
        pilot.credits += credits_gained
        pilot.updated_at = datetime.now(UTC)

        logs.append(f"経験値 +{exp_gained}, クレジット +{credits_gained}")

        # レベルアップチェック
        level_up_count = 0
        while True:
            required_exp = self.calculate_required_exp(pilot.level)
            if pilot.exp >= required_exp:
                pilot.exp -= required_exp
                pilot.level += 1
                level_up_count += 1
                logs.append(f"レベルアップ! Lv.{pilot.level}")
            else:
                break

        if level_up_count > 0:
            logs.append(f"合計 {level_up_count} レベル上昇しました")

        self.session.add(pilot)
        self.session.commit()
        self.session.refresh(pilot)

        return pilot, logs

    def calculate_battle_rewards(
        self,
        win: bool,
        kills: int = 0,
    ) -> tuple[int, int]:
        """バトル結果から報酬を計算する.

        Args:
            win: 勝利したか
            kills: 撃墜数

        Returns:
            tuple[int, int]: (経験値, クレジット)
        """
        if win:
            base_exp = 100
            base_credits = 500
        else:
            base_exp = 20
            base_credits = 100

        # 撃墜ボーナス
        kill_exp = kills * 10
        kill_credits = kills * 50

        total_exp = base_exp + kill_exp
        total_credits = base_credits + kill_credits

        return total_exp, total_credits
