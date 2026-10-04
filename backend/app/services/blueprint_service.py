"""設計図の購入可否判定・付与・一覧取得を行うサービス."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import String, and_, cast
from sqlmodel import Session, col, delete, select

from app.models.models import (
    BlueprintSource,
    BlueprintTargetType,
    BlueprintTechRequirement,
    DropScopeType,
    DropTable,
    DropTableEntry,
    MasterBlueprint,
    MasterBlueprintSettings,
    MasterBlueprintSettingsInput,
    MasterTechnology,
    Mission,
    Pilot,
    PlayerBlueprint,
    PlayerBlueprintResponse,
    TechRequirement,
    TechRequirementStatus,
)
from app.services.drop_source_service import TheaterDropSources
from app.services.technology_service import TechnologyService

# 換金額はアイテムごとに admin-tool で調整する前提の暫定値。
DUPLICATE_CREDIT_RATIO = 0.2

UNAVAILABLE_UNLOCK_HINT = "現在は入手できません"
WIN_ONLY_SUFFIX = "（勝利時のみ）"


@dataclass(frozen=True)
class BlueprintGrantResult:
    """設計図の付与結果."""

    blueprint_id: str
    is_new: bool
    credits_awarded: int


@dataclass(frozen=True)
class UnlockState:
    """ショップでのアイテムの解放状態."""

    is_standard_issue: bool
    is_unlocked: bool
    needs_blueprint: bool
    unlock_hint: str | None = None
    """設計図の入手ヒント。設計図が必要なときだけ入る。"""
    missing_tech_requirements: tuple[TechRequirementStatus, ...] = ()


STANDARD_ISSUE_UNLOCK_STATE = UnlockState(
    is_standard_issue=True, is_unlocked=True, needs_blueprint=False
)


def format_missing_tech(requirement: TechRequirementStatus) -> str:
    """足りない技術Lvを表示用の文言にする."""
    return (
        f"{requirement.tech_name} Lv{requirement.required_lv} が必要"
        f"（現在 Lv{requirement.current_lv}）"
    )


def purchase_denial_message(state: UnlockState, item_label: str) -> str:
    """購入できないアイテムの理由を返す.

    Args:
        state: 未解放のアイテムの解放状態
        item_label: 「機体」「武器」などアイテムの種別の表示名
    """
    if state.needs_blueprint:
        return f"この{item_label}の設計図を所持していません"
    reasons = "、".join(format_missing_tech(r) for r in state.missing_tech_requirements)
    return f"技術Lvが足りません: {reasons}"


class BlueprintService:
    """設計図サービス."""

    @staticmethod
    def blueprint_id_for(target_type: BlueprintTargetType, target_id: str) -> str:
        """対象マスターに対応する設計図IDを返す."""
        return f"{target_type.value.lower()}:{target_id}"

    @staticmethod
    def default_duplicate_credit_value(price: int) -> int:
        """アイテム価格から重複時の換金額の初期値を返す."""
        return int(price * DUPLICATE_CREDIT_RATIO)

    @staticmethod
    def ensure_master_blueprint(
        session: Session,
        target_type: BlueprintTargetType,
        target_id: str,
        price: int,
    ) -> MasterBlueprint:
        """対象マスターの設計図マスターを返す。無ければ標準配備として作成する.

        コミットは呼び出し側で行う。

        Args:
            session: DBセッション
            target_type: 対象の種別
            target_id: 対象の機体マスターID・武器マスターID
            price: 対象アイテムの購入価格。換金額の初期値に使う
        """
        blueprint_id = BlueprintService.blueprint_id_for(target_type, target_id)
        existing = session.get(MasterBlueprint, blueprint_id)
        if existing is not None:
            return existing

        blueprint = MasterBlueprint(
            id=blueprint_id,
            target_type=target_type.value,
            target_id=target_id,
            is_standard_issue=True,
            duplicate_credit_value=BlueprintService.default_duplicate_credit_value(
                price
            ),
        )
        session.add(blueprint)
        return blueprint

    @staticmethod
    def save_master_blueprint_settings(
        session: Session,
        target_type: BlueprintTargetType,
        target_id: str,
        price: int,
        settings: MasterBlueprintSettingsInput | None,
    ) -> MasterBlueprint:
        """対象マスターの設計図設定を保存する.

        設計図マスターが無ければ作成する。`settings` で未指定の項目は変更しない。
        コミットは呼び出し側で行う。

        Args:
            session: DBセッション
            target_type: 対象の種別
            target_id: 対象の機体マスターID・武器マスターID
            price: 対象アイテムの購入価格。設計図マスターを作成するときの換金額の初期値に使う
            settings: 保存する設計図設定
        """
        blueprint = BlueprintService.ensure_master_blueprint(
            session, target_type, target_id, price
        )
        if settings is None:
            return blueprint

        if settings.is_standard_issue is not None:
            blueprint.is_standard_issue = settings.is_standard_issue
        if settings.duplicate_credit_value is not None:
            blueprint.duplicate_credit_value = settings.duplicate_credit_value
        blueprint.updated_at = datetime.now(UTC)
        session.add(blueprint)
        if settings.tech_requirements is not None:
            # 必要な技術Lvの行は設計図マスターを外部キーで参照するため、先に書き込む。
            session.flush()
            TechnologyService.replace_requirements(
                session, blueprint.id, settings.tech_requirements
            )
        return blueprint

    @staticmethod
    def settings_of(
        blueprint: MasterBlueprint | None,
        price: int,
        tech_requirements: list[TechRequirement] | None = None,
    ) -> MasterBlueprintSettings:
        """設計図マスターの設定を返す.

        設計図マスターが無ければ、作成時と同じ初期値を返す。
        `can_purchase` が設計図マスターの無いアイテムを標準配備として扱うことに合わせる。
        `tech_requirements` は `TechnologyService.requirements_by_blueprint` で一括取得した値を渡す。
        """
        if blueprint is None:
            return MasterBlueprintSettings(
                is_standard_issue=True,
                duplicate_credit_value=BlueprintService.default_duplicate_credit_value(
                    price
                ),
            )
        return MasterBlueprintSettings(
            is_standard_issue=blueprint.is_standard_issue,
            duplicate_credit_value=blueprint.duplicate_credit_value,
            tech_requirements=tech_requirements or [],
        )

    @staticmethod
    def saved_settings(
        session: Session, blueprint: MasterBlueprint, price: int
    ) -> MasterBlueprintSettings:
        """保存直後の設計図マスターの設定を、必要な技術Lv付きで返す."""
        requirements = TechnologyService.requirements_by_blueprint(
            session, [blueprint.id]
        )
        return BlueprintService.settings_of(
            blueprint, price, requirements.get(blueprint.id)
        )

    @staticmethod
    def delete_master_blueprint(
        session: Session, target_type: BlueprintTargetType, target_id: str
    ) -> None:
        """対象マスターの設計図マスターと、それを所持している記録を削除する.

        コミットは呼び出し側で行う。
        """
        blueprint_id = BlueprintService.blueprint_id_for(target_type, target_id)
        session.exec(  # type: ignore[call-overload]
            delete(DropTableEntry).where(
                col(DropTableEntry.blueprint_id) == blueprint_id
            )
        )
        session.exec(  # type: ignore[call-overload]
            delete(BlueprintTechRequirement).where(
                col(BlueprintTechRequirement.blueprint_id) == blueprint_id
            )
        )
        session.exec(  # type: ignore[call-overload]
            delete(PlayerBlueprint).where(
                col(PlayerBlueprint.blueprint_id) == blueprint_id
            )
        )
        blueprint = session.get(MasterBlueprint, blueprint_id)
        if blueprint is not None:
            session.delete(blueprint)

    @staticmethod
    def can_purchase(
        session: Session,
        user_id: str,
        target_type: BlueprintTargetType,
        target_id: str,
    ) -> bool:
        """プレイヤーが対象アイテムを購入できるかを返す.

        判定は `get_unlock_states` と同じ。
        """
        return BlueprintService.get_unlock_state(
            session, user_id, target_type, target_id
        ).is_unlocked

    @staticmethod
    def get_unlock_state(
        session: Session,
        user_id: str,
        target_type: BlueprintTargetType,
        target_id: str,
    ) -> UnlockState:
        """対象アイテム1件の解放状態を返す."""
        return BlueprintService.get_unlock_states(
            session, user_id, target_type, [target_id]
        )[target_id]

    @staticmethod
    def get_unlock_states(
        session: Session,
        user_id: str,
        target_type: BlueprintTargetType,
        target_ids: list[str],
    ) -> dict[str, UnlockState]:
        """対象アイテムごとの解放状態を返す.

        標準配備品と、設計図マスターが無いアイテムは購入できる。
        それ以外は、設計図を所持していて、必要な技術Lvをすべて満たせば購入できる。
        設計図が未所持のアイテムには、ドロップテーブルから組み立てた入手ヒントを付ける。
        クエリはアイテム数によらず最大5回。
        """
        standard_issue_by_target = dict(
            session.exec(
                select(MasterBlueprint.target_id, MasterBlueprint.is_standard_issue)
                .where(MasterBlueprint.target_type == target_type.value)
                .where(col(MasterBlueprint.target_id).in_(target_ids))
            ).all()
        )
        owned_targets = set(
            session.exec(
                select(MasterBlueprint.target_id)
                .join(
                    PlayerBlueprint,
                    col(PlayerBlueprint.blueprint_id) == col(MasterBlueprint.id),
                )
                .where(PlayerBlueprint.user_id == user_id)
                .where(MasterBlueprint.target_type == target_type.value)
                .where(col(MasterBlueprint.target_id).in_(target_ids))
            ).all()
        )
        missing_techs = BlueprintService._missing_tech_requirements(
            session, user_id, target_type, target_ids
        )

        locked_targets = [
            target_id
            for target_id in target_ids
            if not standard_issue_by_target.get(target_id, True)
            and target_id not in owned_targets
        ]
        hints = BlueprintService._unlock_hints(session, target_type, locked_targets)

        states: dict[str, UnlockState] = {}
        for target_id in target_ids:
            if standard_issue_by_target.get(target_id, True):
                states[target_id] = STANDARD_ISSUE_UNLOCK_STATE
                continue
            needs_blueprint = target_id not in owned_targets
            missing = tuple(missing_techs.get(target_id, []))
            states[target_id] = UnlockState(
                is_standard_issue=False,
                is_unlocked=not needs_blueprint and not missing,
                needs_blueprint=needs_blueprint,
                unlock_hint=hints[target_id] if needs_blueprint else None,
                missing_tech_requirements=missing,
            )
        return states

    @staticmethod
    def _missing_tech_requirements(
        session: Session,
        user_id: str,
        target_type: BlueprintTargetType,
        target_ids: list[str],
    ) -> dict[str, list[TechRequirementStatus]]:
        """対象アイテムごとに、足りない技術Lvを技術ID順に返す.

        標準配備品は技術Lvを問わないため含めない。
        """
        rows = session.exec(
            select(
                MasterBlueprint.target_id,
                BlueprintTechRequirement.tech_id,
                BlueprintTechRequirement.required_lv,
                MasterTechnology.name,
            )
            .join(
                BlueprintTechRequirement,
                col(BlueprintTechRequirement.blueprint_id) == col(MasterBlueprint.id),
            )
            .join(
                MasterTechnology,
                col(MasterTechnology.id) == col(BlueprintTechRequirement.tech_id),
            )
            .where(MasterBlueprint.target_type == target_type.value)
            .where(col(MasterBlueprint.target_id).in_(target_ids))
            .where(col(MasterBlueprint.is_standard_issue).is_(False))
            .order_by(col(BlueprintTechRequirement.tech_id))
        ).all()
        if not rows:
            return {}

        levels = TechnologyService.levels_by_tech(session, user_id)
        missing: dict[str, list[TechRequirementStatus]] = {}
        for target_id, tech_id, required_lv, tech_name in rows:
            current_lv = levels.get(tech_id, 0)
            if current_lv < required_lv:
                missing.setdefault(target_id, []).append(
                    TechRequirementStatus(
                        tech_id=tech_id,
                        tech_name=tech_name,
                        required_lv=required_lv,
                        current_lv=current_lv,
                    )
                )
        return missing

    @staticmethod
    def _unlock_hints(
        session: Session, target_type: BlueprintTargetType, target_ids: list[str]
    ) -> dict[str, str]:
        """対象アイテムごとに、設計図を入手できる戦闘を示すヒントを返す.

        ミッションをミッションID順に並べ、その後に有効な戦域を巡回順に並べる。
        """
        if not target_ids:
            return {}

        theater_sources = TheaterDropSources.load(session)
        rows = session.exec(
            select(
                MasterBlueprint.target_id,
                DropTable,
                Mission.name,
                DropTableEntry.requires_win,
            )
            .join(
                DropTableEntry,
                col(DropTableEntry.blueprint_id) == col(MasterBlueprint.id),
            )
            .join(DropTable, col(DropTable.id) == col(DropTableEntry.drop_table_id))
            .outerjoin(
                Mission,
                and_(
                    col(DropTable.scope_type) == DropScopeType.MISSION.value,
                    cast(col(Mission.id), String) == col(DropTable.scope_key),
                ),
            )
            .where(MasterBlueprint.target_type == target_type.value)
            .where(col(MasterBlueprint.target_id).in_(target_ids))
            .order_by(col(Mission.id))
        ).all()

        # 対象ID → 表示名 → (表示順, 勝利時のみか)。ミッションの表示順は取得順で決める。
        sources_by_target: dict[str, dict[str, tuple[tuple[int, int], bool]]] = {}
        for target_id, table, mission_name, requires_win in rows:
            if table.scope_type == DropScopeType.MISSION.value:
                labels = [(f"『{mission_name or table.name}』", (0, 0))]
            else:
                labels = [
                    (source.label, (1, source.order))
                    for source in theater_sources.sources_for(
                        table.scope_type, table.scope_key
                    )
                ]
            by_label = sources_by_target.setdefault(target_id, {})
            for label, order in labels:
                _, win_only = by_label.get(label, (order, True))
                by_label[label] = (order, win_only and requires_win)

        return {
            target_id: BlueprintService._format_unlock_hint(
                [
                    (label, requires_win)
                    for label, (_, requires_win) in sorted(
                        sources_by_target.get(target_id, {}).items(),
                        key=lambda item: item[1][0],
                    )
                ]
            )
            for target_id in target_ids
        }

    @staticmethod
    def _format_unlock_hint(sources: list[tuple[str, bool]]) -> str:
        """入手できる戦闘の一覧からヒントの文言を組み立てる.

        Args:
            sources: 戦闘の表示名と、勝利時のみドロップするかの組
        """
        if not sources:
            return UNAVAILABLE_UNLOCK_HINT
        if all(requires_win for _, requires_win in sources):
            labels = "・".join(label for label, _ in sources)
            return f"{labels}でドロップ{WIN_ONLY_SUFFIX}"
        labels = "・".join(
            label + (WIN_ONLY_SUFFIX if requires_win else "")
            for label, requires_win in sources
        )
        return f"{labels}でドロップ"

    @staticmethod
    def grant_blueprint(
        session: Session,
        user_id: str,
        blueprint_id: str,
        source: BlueprintSource,
        source_battle_id: uuid.UUID | None = None,
    ) -> BlueprintGrantResult:
        """プレイヤーに設計図を付与する.

        未所持なら所持記録を作る。所持済みなら換金額分のクレジットを加算する。
        コミットは呼び出し側で行う。

        Raises:
            LookupError: 設計図マスターが無い場合。
                または所持済みで、クレジットを加算するパイロットが無い場合。
        """
        blueprint = session.get(MasterBlueprint, blueprint_id)
        if blueprint is None:
            raise LookupError(f"Blueprint '{blueprint_id}' not found.")

        if BlueprintService._find_owned(session, user_id, blueprint_id) is None:
            session.add(
                PlayerBlueprint(
                    user_id=user_id,
                    blueprint_id=blueprint_id,
                    source=source.value,
                    source_battle_id=source_battle_id,
                )
            )
            return BlueprintGrantResult(
                blueprint_id=blueprint_id, is_new=True, credits_awarded=0
            )

        pilot = session.exec(select(Pilot).where(Pilot.user_id == user_id)).first()
        if pilot is None:
            raise LookupError(f"Pilot for user '{user_id}' not found.")
        pilot.credits += blueprint.duplicate_credit_value
        pilot.updated_at = datetime.now(UTC)
        session.add(pilot)
        return BlueprintGrantResult(
            blueprint_id=blueprint_id,
            is_new=False,
            credits_awarded=blueprint.duplicate_credit_value,
        )

    @staticmethod
    def get_player_blueprints(
        session: Session, user_id: str
    ) -> list[PlayerBlueprintResponse]:
        """プレイヤーの所持設計図を入手日時の古い順に返す."""
        rows = session.exec(
            select(PlayerBlueprint, MasterBlueprint)
            .join(
                MasterBlueprint,
                col(PlayerBlueprint.blueprint_id) == col(MasterBlueprint.id),
            )
            .where(PlayerBlueprint.user_id == user_id)
            .order_by(col(PlayerBlueprint.acquired_at))
        ).all()
        return [
            PlayerBlueprintResponse(
                blueprint_id=owned.blueprint_id,
                target_type=master.target_type,
                target_id=master.target_id,
                source=owned.source,
                source_battle_id=owned.source_battle_id,
                acquired_at=owned.acquired_at,
            )
            for owned, master in rows
        ]

    @staticmethod
    def _find_owned(
        session: Session, user_id: str, blueprint_id: str
    ) -> PlayerBlueprint | None:
        return session.exec(
            select(PlayerBlueprint).where(
                PlayerBlueprint.user_id == user_id,
                PlayerBlueprint.blueprint_id == blueprint_id,
            )
        ).first()
