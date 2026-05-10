# backend/app/services/weapon_service.py
import re

from sqlmodel import Session, select

from app.models.models import MasterWeaponCreate, MasterWeaponUpdate, Pilot


class WeaponService:
    """マスター武器データを操作するサービス."""

    @staticmethod
    def get_master_weapons() -> list[dict]:
        """マスター武器データを全件返す（生JSON辞書形式）."""
        from app.core.gamedata import get_master_weapons

        return get_master_weapons()

    @staticmethod
    def create_master_weapon(data: MasterWeaponCreate) -> dict:
        """マスター武器を新規追加してJSONファイルを永続化する.

        Args:
            data: 新規武器データ

        Returns:
            dict: 追加された武器データ

        Raises:
            LookupError: id が重複している場合
            ValueError: id の形式が不正な場合
        """
        from app.core.gamedata import get_master_weapons, save_master_weapons

        # id バリデーション: スネークケース英数字のみ
        if not re.fullmatch(r"[a-z0-9_]+", data.id):
            raise ValueError(
                f"不正なID形式: '{data.id}'。小文字英数字とアンダースコアのみ使用可能です。"
            )

        current = get_master_weapons()

        # 重複チェック
        if any(item["id"] == data.id for item in current):
            raise LookupError(f"武器ID '{data.id}' は既に存在します。")

        new_entry = data.model_dump()
        # Weapon オブジェクトを辞書に変換
        if hasattr(data.weapon, "model_dump"):
            new_entry["weapon"] = data.weapon.model_dump()

        current.append(new_entry)
        save_master_weapons(current)
        return new_entry

    @staticmethod
    def update_master_weapon(weapon_id: str, data: MasterWeaponUpdate) -> dict | None:
        """既存マスター武器を更新してJSONファイルを永続化する.

        Args:
            weapon_id: 更新対象の武器ID
            data: 更新データ

        Returns:
            dict | None: 更新された武器データ。見つからない場合はNone
        """
        from app.core.gamedata import get_master_weapons, save_master_weapons

        current = get_master_weapons()
        target_index = next(
            (i for i, item in enumerate(current) if item["id"] == weapon_id), None
        )
        if target_index is None:
            return None

        target = current[target_index]

        update_dict = data.model_dump(exclude_unset=True)
        if "weapon" in update_dict and update_dict["weapon"] is not None:
            # Weapon オブジェクトを辞書に変換
            if hasattr(data.weapon, "model_dump"):
                update_dict["weapon"] = data.weapon.model_dump()  # type: ignore[union-attr]
            target["weapon"] = update_dict.pop("weapon")

        target.update(update_dict)
        current[target_index] = target

        save_master_weapons(current)
        return target

    @staticmethod
    def delete_master_weapon(weapon_id: str, session: Session) -> bool:
        """マスター武器を削除してJSONファイルを永続化する.

        Args:
            weapon_id: 削除対象の武器ID
            session: DBセッション（パイロットインベントリ参照チェック用）

        Returns:
            bool: 削除に成功した場合True、対象が存在しない場合False

        Raises:
            LookupError: パイロットのインベントリで参照されている場合
        """
        from app.core.gamedata import get_master_weapons, save_master_weapons

        current = get_master_weapons()
        target_index = next(
            (i for i, item in enumerate(current) if item["id"] == weapon_id), None
        )
        if target_index is None:
            return False

        # パイロットのインベントリ（Pilot.inventory）への参照チェック
        # inventory は {武器ID: 所持数} の辞書形式
        pilots_with_weapon = session.exec(select(Pilot)).all()
        for pilot in pilots_with_weapon:
            if weapon_id in pilot.inventory:
                raise LookupError(
                    f"武器 '{weapon_id}' はパイロットインベントリで参照されています "
                    f"（pilot_id='{pilot.id}'）。"
                    "マスターエントリを削除する前に、全てのパイロットインベントリから削除してください。"
                )

        current.pop(target_index)
        save_master_weapons(current)
        return True
