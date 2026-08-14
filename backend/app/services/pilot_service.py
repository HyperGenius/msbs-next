"""パイロット関連のビジネスロジック."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Session, func, select

from app.core.gamedata import get_shop_listing_by_id
from app.core.npc_data import ACE_PILOTS
from app.core.skills import SKILL_COST, get_skill_definition
from app.models.models import MobileSuit, NpcPilotUpdate, Pilot

# レベルアップ時に付与するステータスポイント数
STATUS_POINTS_PER_LEVEL: int = 2

# npc_data.ACE_PILOTS に由来するパイロット名の集合。
# エースはMobileSuit(user_id=None)として都度生成されPilotテーブルに永続化されないため、
# 名前の一致による best-effort な識別に留める（Issue #441）。
ACE_PILOT_NAMES: frozenset[str] = frozenset(
    str(ace["pilot_name"]) for ace in ACE_PILOTS
)


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

    def build_npc_pilot(self, name: str, personality: str) -> Pilot:
        """NPC パイロットのレコードをメモリ上に構築する（DBアクセスなし）.

        `Pilot.id`/`user_id` はここで確定するため、呼び出し側で複数体を
        `add_all()` してから1回の `flush()`/`commit()` にまとめられる
        （大量生成時の DB ラウンドトリップ削減）。

        Args:
            name: NPC パイロット名
            personality: NPC の性格 (AGGRESSIVE/CAUTIOUS/SNIPER)

        Returns:
            Pilot: セッションにはまだ追加されていない NPC パイロット
        """
        npc_user_id = f"npc-{uuid.uuid4().hex}"
        return Pilot(
            user_id=npc_user_id,
            name=name,
            is_npc=True,
            npc_personality=personality,
            level=1,
            exp=0,
            credits=0,
        )

    def create_npc_pilot(self, name: str, personality: str) -> Pilot:
        """NPC パイロットを新規作成し、即座にDBへ永続化する.

        Args:
            name: NPC パイロット名
            personality: NPC の性格 (AGGRESSIVE/CAUTIOUS/SNIPER)

        Returns:
            Pilot: 作成された NPC パイロット
        """
        pilot = self.build_npc_pilot(name, personality)
        self.session.add(pilot)
        self.session.commit()
        self.session.refresh(pilot)
        return pilot

    def get_npc_pilot(self, user_id: str) -> Pilot | None:
        """NPC パイロットを user_id で取得する.

        Args:
            user_id: NPC の合成 user_id (npc-{uuid} 形式)

        Returns:
            Pilot | None: NPC パイロット。見つからない場合は None
        """
        statement = select(Pilot).where(Pilot.user_id == user_id, Pilot.is_npc == True)  # noqa: E712
        return self.session.exec(statement).first()

    @staticmethod
    def list_npc_pilots(
        session: Session,
        personality: str | None = None,
        min_level: int | None = None,
        max_level: int | None = None,
        ace_only: bool | None = None,
    ) -> list[Pilot]:
        """NPCパイロット一覧を取得する（管理者用）.

        Args:
            session: データベースセッション
            personality: 性格タイプで絞り込む (AGGRESSIVE/CAUTIOUS/SNIPER)
            min_level: レベル下限（この値以上）
            max_level: レベル上限（この値以下）
            ace_only: True の場合エース由来のNPCのみ、False の場合通常NPCのみに絞り込む

        Returns:
            list[Pilot]: NPCパイロットのリスト
        """
        statement = select(Pilot).where(Pilot.is_npc == True)  # noqa: E712
        if personality is not None:
            statement = statement.where(Pilot.npc_personality == personality)
        if min_level is not None:
            statement = statement.where(Pilot.level >= min_level)
        if max_level is not None:
            statement = statement.where(Pilot.level <= max_level)
        if ace_only is True:
            statement = statement.where(Pilot.name.in_(ACE_PILOT_NAMES))  # type: ignore[attr-defined]
        elif ace_only is False:
            statement = statement.where(Pilot.name.not_in(ACE_PILOT_NAMES))  # type: ignore[attr-defined]

        return list(session.exec(statement).all())

    @staticmethod
    def get_npc_pilot_by_id(session: Session, pilot_id: uuid.UUID) -> Pilot | None:
        """NPCパイロットをidで取得する（管理者用）.

        Args:
            session: データベースセッション
            pilot_id: パイロットのUUID

        Returns:
            Pilot | None: NPCパイロット。見つからない場合は None
        """
        statement = select(Pilot).where(
            Pilot.id == pilot_id,
            Pilot.is_npc == True,  # noqa: E712
        )
        return session.exec(statement).first()

    @staticmethod
    def count_owned_mobile_suits_by_user_id(
        session: Session, user_ids: list[str]
    ) -> dict[str, int]:
        """複数NPCの所有機体数を一括取得する（管理者用、一覧表示のN+1回避）.

        Args:
            session: データベースセッション
            user_ids: NPC の合成 user_id (npc-{uuid} 形式) のリスト

        Returns:
            dict[str, int]: user_id -> 所有機体数。0件のuser_idはキーに含まれない
        """
        if not user_ids:
            return {}
        statement = (
            select(MobileSuit.user_id, func.count(MobileSuit.id))  # type: ignore[arg-type]
            .where(MobileSuit.user_id.in_(user_ids))  # type: ignore[union-attr]
            .group_by(MobileSuit.user_id)  # type: ignore[arg-type]
        )
        return dict(session.exec(statement).all())  # type: ignore[arg-type]

    @staticmethod
    def get_npc_owned_mobile_suits(session: Session, user_id: str) -> list[MobileSuit]:
        """NPCパイロットが所有する機体一覧を取得する（管理者用）.

        Args:
            session: データベースセッション
            user_id: NPC の合成 user_id (npc-{uuid} 形式)

        Returns:
            list[MobileSuit]: 所有機体のリスト
        """
        statement = select(MobileSuit).where(MobileSuit.user_id == user_id)
        return list(session.exec(statement).all())

    @staticmethod
    def is_ace_pilot(pilot: Pilot) -> bool:
        """パイロットがエースパイロット由来かどうかを判定する（名前一致によるbest-effort判定）.

        Args:
            pilot: 判定対象のパイロット

        Returns:
            bool: エース由来のNPCの場合 True
        """
        return pilot.name in ACE_PILOT_NAMES

    @staticmethod
    def update_npc_pilot(
        session: Session, pilot_id: uuid.UUID, update_data: NpcPilotUpdate
    ) -> Pilot | None:
        """NPCパイロットのステータスを更新する（管理者用）.

        Args:
            session: データベースセッション
            pilot_id: パイロットのUUID
            update_data: 更新データ

        Returns:
            Pilot | None: 更新後のパイロット。見つからない場合は None
        """
        pilot = PilotService.get_npc_pilot_by_id(session, pilot_id)
        if pilot is None:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(pilot, key, value)
        pilot.updated_at = datetime.now(UTC)

        session.add(pilot)
        session.commit()
        session.refresh(pilot)

        return pilot

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

            # 新規パイロットにスターター機体を付与（デフォルトはzaku_ii）
            self._create_starter_mobile_suit(user_id, "zaku_ii")

        return pilot

    def create_starter_mobile_suit(
        self, user_id: str, unit_id: str = "zaku_ii"
    ) -> MobileSuit:
        """新規パイロットにスターター機体を作成して付与する（公開メソッド）.

        Args:
            user_id: Clerk User ID
            unit_id: 機体ID (デフォルト: "zaku_ii")

        Returns:
            MobileSuit: 作成された機体
        """
        return self._create_starter_mobile_suit(user_id, unit_id)

    def _create_starter_mobile_suit(
        self, user_id: str, unit_id: str = "zaku_ii"
    ) -> MobileSuit:
        """新規パイロットにスターター機体を作成して付与する.

        Args:
            user_id: Clerk User ID
            unit_id: 機体ID (デフォルト: "zaku_ii")

        Returns:
            MobileSuit: 作成された機体
        """
        # 指定された機体をスターター機体として使用
        starter_template = get_shop_listing_by_id(unit_id)
        if not starter_template:
            # フォールバック: テンプレートが見つからない場合はエラー
            raise ValueError(
                f"Starter mobile suit template '{unit_id}' not found in gamedata. "
                f"Check SHOP_LISTINGS in app.core.gamedata to ensure '{unit_id}' is defined."
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
                pilot.status_points += STATUS_POINTS_PER_LEVEL  # ステータスポイント付与
                level_up_count += 1
                logs.append(f"レベルアップ! Lv.{pilot.level}")
            else:
                break

        if level_up_count > 0:
            logs.append(f"合計 {level_up_count} レベル上昇しました")
            logs.append(f"スキルポイント +{level_up_count}")
            logs.append(
                f"ステータスポイント +{level_up_count * STATUS_POINTS_PER_LEVEL}"
            )

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

    def update_pilot_name(self, pilot: Pilot, new_name: str) -> Pilot:
        """パイロット名を更新する.

        Args:
            pilot: 対象パイロット
            new_name: 新しいパイロット名（前後の空白を除去した後、2〜20文字）

        Returns:
            Pilot: 更新後のパイロット

        Raises:
            ValueError: 名前のバリデーションに失敗した場合（空文字・2文字未満・20文字超）
        """
        name = new_name.strip()
        if not name:
            raise ValueError("パイロット名を入力してください")
        if len(name) < 2:
            raise ValueError("パイロット名は2文字以上で入力してください")
        if len(name) > 20:
            raise ValueError("パイロット名は20文字以内で入力してください")

        pilot.name = name
        pilot.updated_at = datetime.now(UTC)

        self.session.add(pilot)
        self.session.commit()
        self.session.refresh(pilot)

        return pilot

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
        # JSON カラムは dict のインプレース変更を SQLAlchemy が追跡できないため、
        # 新しい dict を代入して変更を確実に検知させる
        pilot.skills = {**pilot.skills, skill_id: current_level + 1}
        pilot.skill_points -= SKILL_COST
        pilot.updated_at = datetime.now(UTC)

        self.session.add(pilot)
        self.session.commit()
        self.session.refresh(pilot)

        message = f"{skill_def['name']} Lv.{pilot.skills[skill_id]} を習得しました"
        return pilot, message

    def allocate_status_points(
        self,
        pilot: Pilot,
        sht: int = 0,
        mel: int = 0,
        intel: int = 0,
        ref: int = 0,
        tou: int = 0,
        luk: int = 0,
    ) -> Pilot:
        """ステータスポイントを各ステータスへ割り振る.

        Args:
            pilot: 対象パイロット
            sht: 射撃精度 (SHT) に割り振るポイント数
            mel: 格闘技巧 (MEL) に割り振るポイント数
            intel: 直感 (INT) に割り振るポイント数
            ref: 反応 (REF) に割り振るポイント数
            tou: 耐久 (TOU) に割り振るポイント数
            luk: 幸運 (LUK) に割り振るポイント数

        Returns:
            Pilot: 更新後のパイロット

        Raises:
            ValueError: 割り振りポイントが負、または未使用ポイントを超える場合
        """
        allocations = {
            "sht": sht,
            "mel": mel,
            "intel": intel,
            "ref": ref,
            "tou": tou,
            "luk": luk,
        }

        # 各値が負でないことを確認
        for stat_name, value in allocations.items():
            if value < 0:
                raise ValueError(
                    f"ステータスポイントの割り振りは0以上である必要があります: {stat_name}={value}"
                )

        total_allocated = sum(allocations.values())

        # 未使用ポイントの範囲内か確認
        if total_allocated > pilot.status_points:
            raise ValueError(
                f"ステータスポイントが不足しています (必要: {total_allocated}, 所持: {pilot.status_points})"
            )

        # ステータスに加算
        pilot.sht += sht
        pilot.mel += mel
        pilot.intel += intel
        pilot.ref += ref
        pilot.tou += tou
        pilot.luk += luk
        pilot.status_points -= total_allocated
        pilot.updated_at = datetime.now(UTC)

        self.session.add(pilot)
        self.session.commit()
        self.session.refresh(pilot)

        return pilot
