# backend/app/services/mobile_suit_service.py
import re

from sqlmodel import Session, select

from app.models.models import (
    MasterMobileSuitCreate,
    MasterMobileSuitUpdate,
    MobileSuit,
    MobileSuitUpdate,
)


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
    def get_master_mobile_suits(session: Session) -> list[dict]:
        """マスター機体データを全件返す（生JSON辞書形式）."""
        from app.core.gamedata import get_master_mobile_suits

        return get_master_mobile_suits(session)

    @staticmethod
    def create_master_mobile_suit(session: Session, data: MasterMobileSuitCreate) -> dict:
        """マスター機体を新規追加してDBを永続化する.

        Args:
            session: DBセッション
            data: 新規機体データ

        Returns:
            dict: 追加された機体データ

        Raises:
            ValueError: idが重複している / idの形式が不正 / weaponsが空の場合
        """
        from datetime import UTC, datetime

        from app.core import gamedata as gd
        from app.models.models import MasterMobileSuit

        # idバリデーション: スネークケース英数字のみ
        if not re.fullmatch(r"[a-z0-9_]+", data.id):
            raise ValueError(
                f"Invalid id format: '{data.id}'. Only lowercase alphanumeric and underscore are allowed."
            )

        # weapons 最低1件必須
        if not data.specs.weapons:
            raise ValueError("specs.weapons must have at least one weapon.")

        # 重複チェック
        existing = session.get(MasterMobileSuit, data.id)
        if existing is not None:
            raise LookupError(f"Mobile suit id '{data.id}' already exists.")

        # specs を辞書に変換
        specs_dict = data.specs.model_dump()
        specs_dict["weapons"] = [w.model_dump() for w in data.specs.weapons]

        # INSERT
        record = MasterMobileSuit(
            id=data.id,
            name=data.name,
            price=data.price,
            faction=data.faction,
            description=data.description,
            specs=specs_dict,
        )
        session.add(record)
        session.commit()

        # キャッシュを無効化
        gd._shop_listings_cache = None
        gd._cache_expires_at = None

        return {
            "id": data.id,
            "name": data.name,
            "price": data.price,
            "faction": data.faction,
            "description": data.description,
            "specs": specs_dict,
        }

    @staticmethod
    def update_master_mobile_suit(
        session: Session, ms_id: str, data: MasterMobileSuitUpdate
    ) -> dict | None:
        """既存マスター機体を更新してDBを永続化する.

        Args:
            session: DBセッション
            ms_id: 更新対象の機体ID
            data: 更新データ

        Returns:
            dict | None: 更新された機体データ。見つからない場合はNone

        Raises:
            ValueError: weaponsが空になる場合
        """
        from datetime import UTC, datetime

        from app.core import gamedata as gd
        from app.models.models import MasterMobileSuit

        record = session.get(MasterMobileSuit, ms_id)
        if record is None:
            return None

        update_dict = data.model_dump(exclude_unset=True)

        if "specs" in update_dict and update_dict["specs"] is not None:
            specs_data = update_dict["specs"]
            if "weapons" in specs_data:
                if not specs_data["weapons"]:
                    raise ValueError("specs.weapons must have at least one weapon.")
                specs_data["weapons"] = [
                    w.model_dump() if hasattr(w, "model_dump") else w
                    for w in data.specs.weapons  # type: ignore[union-attr]
                ]
            # 既存 specs とマージ
            existing_specs = dict(record.specs)
            existing_specs.update(specs_data)
            record.specs = existing_specs
            update_dict.pop("specs")

        for key, value in update_dict.items():
            setattr(record, key, value)

        record.updated_at = datetime.now(UTC)
        session.add(record)
        session.commit()

        # キャッシュを無効化
        gd._shop_listings_cache = None
        gd._cache_expires_at = None

        return {
            "id": record.id,
            "name": record.name,
            "price": record.price,
            "faction": record.faction,
            "description": record.description,
            "specs": record.specs,
        }

    @staticmethod
    def delete_master_mobile_suit(ms_id: str, session: Session) -> bool:
        """マスター機体を削除してDBを永続化する.

        Args:
            ms_id: 削除対象の機体ID
            session: DBセッション（ショップ在庫参照チェック用）

        Returns:
            bool: 削除に成功した場合True、対象が存在しない場合False

        Raises:
            LookupError: ショップ在庫で参照されている場合
        """
        from app.core import gamedata as gd
        from app.models.models import MasterMobileSuit

        record = session.get(MasterMobileSuit, ms_id)
        if record is None:
            return False

        # ショップ在庫（プレイヤーが所有する機体）への参照チェック
        ms_name = record.name
        existing_ms = session.exec(
            select(MobileSuit).where(MobileSuit.name == ms_name)
        ).first()
        if existing_ms is not None:
            raise LookupError(
                f"Mobile suit '{ms_id}' is referenced in shop inventory (name='{ms_name}'). "
                "Remove all owned copies before deleting the master entry."
            )

        session.delete(record)
        session.commit()

        # キャッシュを無効化
        gd._shop_listings_cache = None
        gd._cache_expires_at = None

        return True
