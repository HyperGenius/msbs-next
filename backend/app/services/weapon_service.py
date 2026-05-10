"""武器インスタンス管理サービス."""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.gamedata import get_weapon_listing_by_id
from app.engine.constants import MAX_WEAPON_SLOTS
from app.models.models import MobileSuit, Pilot, PlayerWeapon, Weapon


class WeaponService:
    """武器インスタンスを操作するサービス."""

    @staticmethod
    def purchase_weapon(session: Session, user_id: str, weapon_id: str) -> PlayerWeapon:
        """武器を購入して PlayerWeapon 行を INSERT する.

        Args:
            session: データベースセッション
            user_id: 購入者のユーザーID
            weapon_id: 購入する武器ID

        Returns:
            PlayerWeapon: 作成された武器インスタンス

        Raises:
            HTTPException: 武器が存在しない、パイロット情報がない、所持金不足などのエラー
        """
        listing = get_weapon_listing_by_id(weapon_id)
        if not listing:
            raise HTTPException(status_code=404, detail="武器が見つかりません")

        statement = select(Pilot).where(Pilot.user_id == user_id)
        pilot = session.exec(statement).first()
        if not pilot:
            raise HTTPException(status_code=404, detail="パイロット情報が見つかりません")

        if pilot.credits < listing["price"]:
            raise HTTPException(
                status_code=400,
                detail=f"所持金が不足しています。必要: {listing['price']} Credits, 所持: {pilot.credits} Credits",
            )

        # 所持金を減算
        pilot.credits -= listing["price"]

        # 後方互換性のため inventory も更新する
        if pilot.inventory is None:
            pilot.inventory = {}
        current_count = pilot.inventory.get(weapon_id, 0)
        pilot.inventory = {**pilot.inventory, weapon_id: current_count + 1}

        pilot.updated_at = datetime.now(UTC)

        # Weapon スペックスナップショットを取得
        weapon_obj: Weapon = listing["weapon"]
        base_snapshot = weapon_obj.model_dump()

        player_weapon = PlayerWeapon(
            user_id=user_id,
            master_weapon_id=weapon_id,
            base_snapshot=base_snapshot,
            custom_stats={},
        )

        session.add(pilot)
        session.add(player_weapon)
        session.commit()
        session.refresh(pilot)
        session.refresh(player_weapon)

        return player_weapon

    @staticmethod
    def equip_weapon(
        session: Session,
        user_id: str,
        player_weapon_id: uuid.UUID,
        ms_id: uuid.UUID,
        slot_index: int,
    ) -> MobileSuit:
        """PlayerWeapon を指定機体のスロットに装備する.

        Args:
            session: データベースセッション
            user_id: 操作ユーザーID
            player_weapon_id: 装備する PlayerWeapon の UUID
            ms_id: 装備先機体の UUID
            slot_index: 装備スロット（0=メイン, 1=サブ）

        Returns:
            MobileSuit: 更新された機体

        Raises:
            HTTPException: 権限エラー・未装備チェック・スロット検証などのエラー
        """
        if slot_index < 0 or slot_index >= MAX_WEAPON_SLOTS:
            raise HTTPException(
                status_code=400,
                detail="スロットインデックスが範囲外です (有効: 0=メイン武器, 1=サブ武器)",
            )

        player_weapon = session.get(PlayerWeapon, player_weapon_id)
        if not player_weapon:
            raise HTTPException(status_code=404, detail="武器インスタンスが見つかりません")

        if player_weapon.user_id != user_id:
            raise HTTPException(status_code=403, detail="この武器インスタンスへのアクセス権がありません")

        # 既に別の機体に装備中の場合は 400
        if player_weapon.equipped_ms_id is not None and player_weapon.equipped_ms_id != ms_id:
            raise HTTPException(status_code=400, detail="この武器は別の機体に装備中です")

        # 同スロットに既に別の PlayerWeapon が入っている場合は外す
        existing_stmt = (
            select(PlayerWeapon)
            .where(PlayerWeapon.equipped_ms_id == ms_id)
            .where(PlayerWeapon.equipped_slot == slot_index)
            .where(PlayerWeapon.id != player_weapon_id)
        )
        existing_pw = session.exec(existing_stmt).first()
        if existing_pw:
            existing_pw.equipped_ms_id = None
            existing_pw.equipped_slot = None
            session.add(existing_pw)

        mobile_suit = session.get(MobileSuit, ms_id)
        if not mobile_suit:
            raise HTTPException(status_code=404, detail="機体が見つかりません")

        if mobile_suit.user_id != user_id:
            raise HTTPException(status_code=403, detail="この機体を編集する権限がありません")

        # PlayerWeapon を更新
        player_weapon.equipped_ms_id = ms_id
        player_weapon.equipped_slot = slot_index
        session.add(player_weapon)

        # 後方互換性のため MobileSuit.weapons も更新する
        weapon_obj = Weapon(**player_weapon.base_snapshot)
        new_weapons = list(mobile_suit.weapons or [])
        if slot_index >= len(new_weapons):
            new_weapons.append(weapon_obj)
        else:
            new_weapons[slot_index] = weapon_obj
        mobile_suit.weapons = new_weapons

        session.add(mobile_suit)
        session.commit()
        session.refresh(mobile_suit)

        return mobile_suit

    @staticmethod
    def unequip_weapon(
        session: Session, user_id: str, player_weapon_id: uuid.UUID
    ) -> PlayerWeapon:
        """PlayerWeapon の装備を外す.

        Args:
            session: データベースセッション
            user_id: 操作ユーザーID
            player_weapon_id: 外す PlayerWeapon の UUID

        Returns:
            PlayerWeapon: 更新された武器インスタンス

        Raises:
            HTTPException: 権限エラーなど
        """
        player_weapon = session.get(PlayerWeapon, player_weapon_id)
        if not player_weapon:
            raise HTTPException(status_code=404, detail="武器インスタンスが見つかりません")

        if player_weapon.user_id != user_id:
            raise HTTPException(status_code=403, detail="この武器インスタンスへのアクセス権がありません")

        player_weapon.equipped_ms_id = None
        player_weapon.equipped_slot = None
        session.add(player_weapon)
        session.commit()
        session.refresh(player_weapon)

        return player_weapon

    @staticmethod
    def get_player_weapons(
        session: Session, user_id: str, unequipped_only: bool = False
    ) -> list[PlayerWeapon]:
        """ログインユーザーの所有武器インスタンス一覧を返す.

        Args:
            session: データベースセッション
            user_id: 操作ユーザーID
            unequipped_only: True の場合、未装備の武器のみ返す

        Returns:
            list[PlayerWeapon]: 所有武器インスタンス一覧
        """
        statement = select(PlayerWeapon).where(PlayerWeapon.user_id == user_id)
        if unequipped_only:
            statement = statement.where(PlayerWeapon.equipped_ms_id == None)  # noqa: E711
        results = session.exec(statement).all()
        return list(results)
