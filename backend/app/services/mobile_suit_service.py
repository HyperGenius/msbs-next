# backend/app/services/mobile_suit_service.py
import re

from sqlmodel import Session, select

from app.models.models import MobileSuit, MobileSuitUpdate, MasterMobileSuitCreate, MasterMobileSuitUpdate


class MobileSuitService:
    """機体データを操作するサービス."""

    @staticmethod
    def get_all_mobile_suits(session: Session, user_id: str) -> list[MobileSuit]:
        """指定ユーザーが所有する機体データを取得する."""
        statement = (
            select(MobileSuit)
            .where(MobileSuit.user_id == user_id)
            .order_by(MobileSuit.name)
        )
        results = session.exec(statement).all()
        return list(results)

    @staticmethod
    def update_mobile_suit(
        session: Session, ms_id: str, update_data: MobileSuitUpdate
    ) -> MobileSuit | None:
        """機体データを更新する."""
        # IDで検索
        statement = select(MobileSuit).where(MobileSuit.id == ms_id)
        ms = session.exec(statement).first()

        if not ms:
            return None

        # データの更新 (Pydantic v2 style)
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(ms, key, value)

        session.add(ms)
        session.commit()
        session.refresh(ms)

        return ms

    # --- マスター機体データ CRUD ---

    @staticmethod
    def get_master_mobile_suits() -> list[dict]:
        """マスター機体データを全件返す（生JSON辞書形式）."""
        from app.core.gamedata import get_master_mobile_suits
        return get_master_mobile_suits()

    @staticmethod
    def create_master_mobile_suit(data: MasterMobileSuitCreate) -> dict:
        """マスター機体を新規追加してJSONファイルを永続化する.

        Args:
            data: 新規機体データ

        Returns:
            dict: 追加された機体データ

        Raises:
            ValueError: idが重複している / idの形式が不正 / weaponsが空の場合
        """
        from app.core.gamedata import get_master_mobile_suits, save_master_mobile_suits

        # idバリデーション: スネークケース英数字のみ
        if not re.fullmatch(r"[a-z0-9_]+", data.id):
            raise ValueError(f"Invalid id format: '{data.id}'. Only lowercase alphanumeric and underscore are allowed.")

        # weapons 最低1件必須
        if not data.specs.weapons:
            raise ValueError("specs.weapons must have at least one weapon.")

        current = get_master_mobile_suits()

        # 重複チェック
        if any(item["id"] == data.id for item in current):
            raise LookupError(f"Mobile suit id '{data.id}' already exists.")

        new_entry = data.model_dump()
        # Weapon オブジェクトを辞書に変換
        new_entry["specs"]["weapons"] = [w.model_dump() for w in data.specs.weapons]

        current.append(new_entry)
        save_master_mobile_suits(current)
        return new_entry

    @staticmethod
    def update_master_mobile_suit(ms_id: str, data: MasterMobileSuitUpdate) -> dict | None:
        """既存マスター機体を更新してJSONファイルを永続化する.

        Args:
            ms_id: 更新対象の機体ID
            data: 更新データ

        Returns:
            dict | None: 更新された機体データ。見つからない場合はNone

        Raises:
            ValueError: weaponsが空になる場合
        """
        from app.core.gamedata import get_master_mobile_suits, save_master_mobile_suits

        current = get_master_mobile_suits()
        target_index = next((i for i, item in enumerate(current) if item["id"] == ms_id), None)
        if target_index is None:
            return None

        target = current[target_index]

        update_dict = data.model_dump(exclude_unset=True)
        if "specs" in update_dict and update_dict["specs"] is not None:
            # Weapon オブジェクトを辞書に変換
            specs_data = update_dict["specs"]
            if "weapons" in specs_data:
                if not specs_data["weapons"]:
                    raise ValueError("specs.weapons must have at least one weapon.")
                specs_data["weapons"] = [
                    w.model_dump() if hasattr(w, "model_dump") else w
                    for w in data.specs.weapons  # type: ignore[union-attr]
                ]
            target["specs"].update(specs_data)
            update_dict.pop("specs")

        target.update(update_dict)
        current[target_index] = target

        save_master_mobile_suits(current)
        return target

    @staticmethod
    def delete_master_mobile_suit(ms_id: str, session: Session) -> bool:
        """マスター機体を削除してJSONファイルを永続化する.

        Args:
            ms_id: 削除対象の機体ID
            session: DBセッション（ショップ在庫参照チェック用）

        Returns:
            bool: 削除に成功した場合True、対象が存在しない場合False

        Raises:
            LookupError: ショップ在庫で参照されている場合
        """
        from app.core.gamedata import get_master_mobile_suits, save_master_mobile_suits

        current = get_master_mobile_suits()
        target_index = next((i for i, item in enumerate(current) if item["id"] == ms_id), None)
        if target_index is None:
            return False

        # ショップ在庫（プレイヤーが所有する機体）への参照チェック
        # mobile_suits テーブルで master_id がある場合に照合
        # 現在の設計では購入済み機体に master_id カラムはないが、
        # 将来の参照整合性のため name マッチングで確認する
        # （既存設計に従い、より安全な削除のために name を比較）
        ms_name = current[target_index]["name"]
        existing_ms = session.exec(
            select(MobileSuit).where(MobileSuit.name == ms_name)
        ).first()
        if existing_ms is not None:
            raise LookupError(
                f"Mobile suit '{ms_id}' is referenced in shop inventory (name='{ms_name}'). "
                "Remove all owned copies before deleting the master entry."
            )

        current.pop(target_index)
        save_master_mobile_suits(current)
        return True
