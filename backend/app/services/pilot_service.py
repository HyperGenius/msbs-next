"""パイロット関連のビジネスロジック."""

from datetime import UTC, datetime

from sqlmodel import Session, select

from app.core.gamedata import SHOP_LISTINGS, get_shop_listing_by_id
from app.core.skills import SKILL_COST, get_skill_definition
from app.models.models import MobileSuit, Pilot


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

            # 新規パイロットにスターター機体を付与
            self._create_starter_mobile_suit(user_id)

        return pilot

    def _create_starter_mobile_suit(self, user_id: str) -> MobileSuit:
        """新規パイロットにスターター機体を作成して付与する.

        Args:
            user_id: Clerk User ID

        Returns:
            MobileSuit: 作成された機体
        """
        # Zaku II をスターター機体として使用
        starter_template = get_shop_listing_by_id("zaku_ii")
        if not starter_template:
            # フォールバック: テンプレートが見つからない場合はエラー
            raise ValueError(
                "Starter mobile suit template 'zaku_ii' not found in gamedata. "
                "Check SHOP_LISTINGS in app.core.gamedata to ensure 'zaku_ii' is defined."
            )

        specs = starter_template["specs"]

        # スターター機体を作成
        starter_suit = MobileSuit(
            user_id=user_id,
            name=f"{starter_template['name']} (Starter)",
            max_hp=specs["max_hp"],
            current_hp=specs["max_hp"],
            armor=specs["armor"],
            mobility=specs["mobility"],
            sensor_range=specs.get("sensor_range", 500.0),
            beam_resistance=specs.get("beam_resistance", 0.0),
            physical_resistance=specs.get("physical_resistance", 0.0),
            weapons=specs["weapons"],
            side="PLAYER",
        )

        self.session.add(starter_suit)
        self.session.commit()
        self.session.refresh(starter_suit)

        return starter_suit

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
                pilot.skill_points += 1  # レベルアップ時にSP付与
                level_up_count += 1
                logs.append(f"レベルアップ! Lv.{pilot.level}")
            else:
                break

        if level_up_count > 0:
            logs.append(f"合計 {level_up_count} レベル上昇しました")
            logs.append(f"スキルポイント +{level_up_count}")

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

    def unlock_skill(self, pilot: Pilot, skill_id: str) -> tuple[Pilot, str]:
        """スキルを習得または強化する.

        Args:
            pilot: 対象パイロット
            skill_id: スキルID

        Returns:
            tuple[Pilot, str]: 更新後のパイロットとメッセージ

        Raises:
            ValueError: スキルが存在しない、SPが不足している、または最大レベルに達している場合
        """
        # スキル定義を取得
        skill_def = get_skill_definition(skill_id)
        if not skill_def:
            raise ValueError(f"スキルが見つかりません: {skill_id}")

        # 現在のスキルレベルを取得
        current_level = pilot.skills.get(skill_id, 0)

        # 最大レベルチェック
        if current_level >= skill_def["max_level"]:
            raise ValueError(f"スキル {skill_def['name']} は最大レベルに達しています")

        # SPチェック
        if pilot.skill_points < SKILL_COST:
            raise ValueError(f"スキルポイントが不足しています (必要: {SKILL_COST})")

        # スキルレベルアップとSP消費
        pilot.skills[skill_id] = current_level + 1
        pilot.skill_points -= SKILL_COST
        pilot.updated_at = datetime.now(UTC)

        self.session.add(pilot)
        self.session.commit()
        self.session.refresh(pilot)

        message = f"{skill_def['name']} Lv.{pilot.skills[skill_id]} を習得しました"
        return pilot, message
