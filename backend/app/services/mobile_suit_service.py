# backend/app/services/mobile_suit_service.py
import re

from sqlmodel import Session, select

from app.models.models import (
    MasterMobileSuit,
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
    def get_master_mobile_suit_map(
        session: Session, names: list[str]
    ) -> dict[str, MasterMobileSuit]:
        """機体名からマスター機体レコードを引くためのマップを返す.

        プレイヤー所持機体 (MobileSuit) はマスター機体 (MasterMobileSuit) と
        name で紐づいているため、名前をキーに検索する
        （weapon_slot_count / beam_generator_lv など複数フィールドの参照に使う）。
        """
        if not names:
            return {}
        statement = select(MasterMobileSuit).where(
            MasterMobileSuit.name.in_(set(names))  # type: ignore[attr-defined]
        )
        records = session.exec(statement).all()
        return {r.name: r for r in records}

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
    def create_master_mobile_suit(
        session: Session, data: MasterMobileSuitCreate
    ) -> dict:
        """マスター機体を新規追加してDBを永続化する.

        Args:
            session: DBセッション
            data: 新規機体データ

        Returns:
            dict: 追加された機体データ

        Raises:
            ValueError: idが重複している / idの形式が不正 / weaponsが空の場合
        """
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

        MobileSuitService._validate_weapon_constraints(
            data.specs.weapons, data.weapon_slot_count, data.beam_generator_lv
        )

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
            name_ja=data.name_ja,
            model_number=data.model_number,
            price=data.price,
            faction=data.faction,
            description=data.description,
            weapon_slot_count=data.weapon_slot_count,
            beam_generator_lv=data.beam_generator_lv,
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
            "name_ja": data.name_ja,
            "model_number": data.model_number,
            "price": data.price,
            "faction": data.faction,
            "description": data.description,
            "weapon_slot_count": data.weapon_slot_count,
            "beam_generator_lv": data.beam_generator_lv,
            "specs": specs_dict,
        }

    @staticmethod
    def _validate_weapon_constraints(
        weapons: list, weapon_slot_count: int, beam_generator_lv: int
    ) -> None:
        """武器スロット数・ビームジェネレータLvの制約を検証する.

        Args:
            weapons: 検証対象の武器リスト (Weapon または dict)
            weapon_slot_count: 装備可能な武器スロット数
            beam_generator_lv: 機体のビームジェネレータLv

        Raises:
            ValueError: 武器数がスロット数を超える、または要求ビームLvが
                機体のビームジェネレータLvを超えるビーム属性武器が含まれる場合
        """
        if len(weapons) > weapon_slot_count:
            raise ValueError(
                f"Number of weapons ({len(weapons)}) exceeds weapon_slot_count "
                f"({weapon_slot_count})."
            )
        for w in weapons:
            w_type = w.type if hasattr(w, "type") else w.get("type", "PHYSICAL")
            required_lv = (
                w.required_beam_generator_lv
                if hasattr(w, "required_beam_generator_lv")
                else w.get("required_beam_generator_lv", 0)
            )
            if w_type == "BEAM" and required_lv > beam_generator_lv:
                w_name = w.name if hasattr(w, "name") else w.get("name", "?")
                raise ValueError(
                    f"Weapon '{w_name}' requires beam_generator_lv "
                    f"{required_lv}, but the mobile suit's beam_generator_lv "
                    f"is {beam_generator_lv}."
                )

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

        weapon_slot_count = update_dict.get(
            "weapon_slot_count", record.weapon_slot_count
        )
        beam_generator_lv = update_dict.get(
            "beam_generator_lv", record.beam_generator_lv
        )
        MobileSuitService._validate_weapon_constraints(
            record.specs.get("weapons", []), weapon_slot_count, beam_generator_lv
        )

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
            "name_ja": record.name_ja,
            "model_number": record.model_number,
            "price": record.price,
            "faction": record.faction,
            "description": record.description,
            "weapon_slot_count": record.weapon_slot_count,
            "beam_generator_lv": record.beam_generator_lv,
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
