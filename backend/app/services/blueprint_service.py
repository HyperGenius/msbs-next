"""設計図の購入可否判定・付与・一覧取得を行うサービス."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlmodel import Session, col, delete, select

from app.models.models import (
    BlueprintSource,
    BlueprintTargetType,
    MasterBlueprint,
    Pilot,
    PlayerBlueprint,
    PlayerBlueprintResponse,
)

# 換金額はアイテムごとに admin-tool で調整する前提の暫定値。
DUPLICATE_CREDIT_RATIO = 0.2


@dataclass(frozen=True)
class BlueprintGrantResult:
    """設計図の付与結果."""

    blueprint_id: str
    is_new: bool
    credits_awarded: int


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
    def delete_master_blueprint(
        session: Session, target_type: BlueprintTargetType, target_id: str
    ) -> None:
        """対象マスターの設計図マスターと、それを所持している記録を削除する.

        コミットは呼び出し側で行う。
        """
        blueprint_id = BlueprintService.blueprint_id_for(target_type, target_id)
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

        標準配備品か、設計図を所持していれば購入できる。
        設計図マスターが無いアイテムは、導入前と同じく購入できる扱いにする。
        """
        blueprint_id = BlueprintService.blueprint_id_for(target_type, target_id)
        blueprint = session.get(MasterBlueprint, blueprint_id)
        if blueprint is None or blueprint.is_standard_issue:
            return True
        return BlueprintService._find_owned(session, user_id, blueprint_id) is not None

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
