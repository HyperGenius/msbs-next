# backend/app/services/mobile_suit_service.py
import re
import uuid
from datetime import UTC, datetime

from sqlmodel import Session, and_, col, select

from app.core.npc_data import build_npc_tactics
from app.engine.constants import (
    TACTICS_PRIORITIES,
    TACTICS_RANGES,
    WEAPON_SWITCH_POLICIES,
)
from app.models.models import (
    ALL_PART_NAMES,
    BlueprintTargetType,
    MasterBlueprint,
    MasterBlueprintSettings,
    MasterMobileSuit,
    MasterMobileSuitCreate,
    MasterMobileSuitUpdate,
    MasterWeapon,
    MobileSuit,
    MobileSuitUpdate,
    NpcMobileSuitUpdate,
    Pilot,
    Weapon,
    resolve_weapon_slot_count,
)
from app.services.blueprint_service import BlueprintService
from app.services.weapon_service import validate_aim_distribution

# 機体マスターの specs から MobileSuit へそのままコピーする項目（weapons は別途変換する）。
_MASTER_SPEC_FIELDS = (
    "max_hp",
    "armor",
    "mobility",
    "sensor_range",
    "beam_resistance",
    "physical_resistance",
    "melee_aptitude",
    "shooting_aptitude",
    "accuracy_bonus",
    "evasion_bonus",
    "acceleration_bonus",
    "turning_bonus",
    "missing_parts",
)


def _master_mobile_suit_to_dict(
    record: MasterMobileSuit, blueprint: MasterBlueprintSettings
) -> dict:
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
        "flavor_text": record.flavor_text,
        "specs": record.specs,
        "blueprint": blueprint.model_dump(),
    }


def _validate_missing_parts(missing_parts: list[str]) -> None:
    invalid_parts = [p for p in missing_parts if p not in ALL_PART_NAMES]
    if invalid_parts:
        raise ValueError(
            f"Invalid missing_parts: {invalid_parts}. Must be any of {ALL_PART_NAMES}."
        )


def validate_npc_weapons(weapons: list[Weapon], weapon_slot_count: int) -> None:
    """NPC 機・エース機の武装が武器スロット数に収まり、武器 ID が重複しないことを検証する.

    バトル中の弾数・クールダウンは武器 ID をキーに持つため、同じ ID の武器は状態を共有してしまう。
    ビームジェネレータLv の条件は NPC 機・エース機には適用しない。

    Raises:
        ValueError: 武装の本数がスロット数を超える、または武器 ID が重複する場合
    """
    if len(weapons) > weapon_slot_count:
        raise ValueError(
            f"Number of weapons ({len(weapons)}) exceeds weapon_slot_count "
            f"({weapon_slot_count})."
        )
    seen: set[str] = set()
    duplicated: list[str] = []
    for w in weapons:
        if w.id in seen and w.id not in duplicated:
            duplicated.append(w.id)
        seen.add(w.id)
    if duplicated:
        raise ValueError(f"Duplicate weapon ids: {duplicated}.")


def validate_tactics(tactics: dict) -> None:
    """戦術設定の priority / range / weapon_switch_policy が許容値かを検証する.

    未設定のキーはエンジン側の既定値で動くため、検証しない。
    それ以外のキーも保存時に消さないため、検証しない。

    Raises:
        ValueError: いずれかの値が許容値に無い場合
    """
    for key, allowed in (
        ("priority", TACTICS_PRIORITIES),
        ("range", TACTICS_RANGES),
        ("weapon_switch_policy", WEAPON_SWITCH_POLICIES),
    ):
        if key in tactics and tactics[key] not in allowed:
            raise ValueError(
                f"Invalid tactics.{key}: {tactics[key]!r}. Must be one of {allowed}."
            )


def validate_weapon_aim_distributions(weapons: list[Weapon]) -> None:
    """各武器の狙う部位配分を検証する.

    Raises:
        ValueError: いずれかの武器の配分が不正な場合
    """
    for w in weapons:
        try:
            validate_aim_distribution(w.aim_distribution)
        except ValueError as e:
            raise ValueError(f"Invalid aim_distribution of weapon '{w.id}': {e}") from e


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
        session: Session, ms_id: str | uuid.UUID, update_data: MobileSuitUpdate
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

    # --- NPC 機体（管理者用） ---

    @staticmethod
    def update_npc_mobile_suit(
        session: Session, ms: MobileSuit, update_data: NpcMobileSuitUpdate
    ) -> MobileSuit:
        """NPC 機体を更新する.

        Raises:
            ValueError: 武装が空、武装がスロット数を超える、武器 ID が重複する、
                欠損部位名・戦術・狙う部位配分が不正な場合
        """
        if update_data.weapons is not None:
            if not update_data.weapons:
                raise ValueError("weapons must have at least one weapon.")
            validate_weapon_aim_distributions(update_data.weapons)
        if update_data.missing_parts is not None:
            _validate_missing_parts(update_data.missing_parts)
        if update_data.tactics is not None:
            validate_tactics(update_data.tactics)
        if update_data.weapons is not None or update_data.weapon_slot_count is not None:
            validate_npc_weapons(
                update_data.weapons
                if update_data.weapons is not None
                else [Weapon.model_validate(w) for w in ms.weapons],
                update_data.weapon_slot_count or resolve_weapon_slot_count(ms),
            )

        # None は「未指定」として扱う。NOT NULL 列を壊さないため。
        update_dict = {
            key: value
            for key, value in update_data.model_dump(exclude_unset=True).items()
            if value is not None
        }
        for key, value in update_dict.items():
            setattr(ms, key, value)
        if update_data.weapons is not None:
            ms.weapons = update_data.weapons

        if update_data.max_hp is not None:
            ms.current_hp = ms.max_hp
        # parts は max_hp/armor/missing_parts から派生する。空にすると normalize_parts() が再生成する。
        if {"max_hp", "armor", "missing_parts"} & update_dict.keys():
            ms.parts = {}

        session.add(ms)
        session.commit()
        session.refresh(ms)
        return ms

    @staticmethod
    def create_npc_mobile_suit_from_master(
        session: Session, pilot: Pilot, master_id: str
    ) -> MobileSuit | None:
        """機体マスターのスペックをコピーして NPC 機体を作成する.

        NPC の出撃機体が未設定の場合は、作成した機体を出撃機体に設定する。

        Returns:
            作成した機体。機体マスターが存在しない場合は None
        """
        master = session.get(MasterMobileSuit, master_id)
        if master is None:
            return None

        specs = master.specs
        weapons = [Weapon(**w) for w in specs["weapons"]]
        # 機体マスターの武器は武器マスターにない ID も持てるため、存在する ID だけ記録する。
        existing_weapon_ids = set(
            session.exec(
                select(MasterWeapon.id).where(
                    col(MasterWeapon.id).in_([w.id for w in weapons])
                )
            ).all()
        )
        for weapon in weapons:
            if weapon.id in existing_weapon_ids:
                weapon.master_weapon_id = weapon.id
        personality = pilot.npc_personality or "AGGRESSIVE"
        ms = MobileSuit(
            **{k: specs[k] for k in _MASTER_SPEC_FIELDS if k in specs},
            name=f"{master.name} (NPC)",
            current_hp=specs["max_hp"],
            weapons=weapons,
            weapon_slot_count=master.weapon_slot_count,
            master_mobile_suit_id=master.id,
            user_id=pilot.user_id,
            side="ENEMY",
            tactics=build_npc_tactics(personality),
            personality=personality,
            pilot_name=pilot.name,
        )
        session.add(ms)
        # flush で機体を先に INSERT してから出撃機体に設定する（FK 違反防止）
        session.flush()
        if pilot.active_mobile_suit_id is None:
            pilot.active_mobile_suit_id = ms.id
            pilot.updated_at = datetime.now(UTC)
            session.add(pilot)
        session.commit()
        session.refresh(ms)
        return ms

    # --- マスター機体データ CRUD ---

    @staticmethod
    def get_master_mobile_suits(session: Session) -> list[dict]:
        """マスター機体データを設計図設定付きで全件返す（生JSON辞書形式）."""
        rows = session.exec(
            select(MasterMobileSuit, MasterBlueprint).outerjoin(
                MasterBlueprint,
                and_(
                    col(MasterBlueprint.target_type)
                    == BlueprintTargetType.MOBILE_SUIT.value,
                    col(MasterBlueprint.target_id) == col(MasterMobileSuit.id),
                ),
            )
        ).all()
        return [
            _master_mobile_suit_to_dict(
                record, BlueprintService.settings_of(blueprint, record.price)
            )
            for record, blueprint in rows
        ]

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
            flavor_text=data.flavor_text,
            specs=specs_dict,
        )
        session.add(record)
        blueprint = BlueprintService.save_master_blueprint_settings(
            session,
            BlueprintTargetType.MOBILE_SUIT,
            data.id,
            data.price,
            data.blueprint,
        )
        session.commit()

        # キャッシュを無効化
        gd._shop_listings_cache = None
        gd._cache_expires_at = None

        return _master_mobile_suit_to_dict(
            record, BlueprintService.settings_of(blueprint, record.price)
        )

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

        record = session.get(MasterMobileSuit, ms_id)
        if record is None:
            return None

        update_dict = data.model_dump(exclude_unset=True)
        update_dict.pop("blueprint", None)

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
        # 換金額は価格に追従させない。運用者が明示的に決める値のため。
        blueprint = BlueprintService.save_master_blueprint_settings(
            session,
            BlueprintTargetType.MOBILE_SUIT,
            ms_id,
            record.price,
            data.blueprint,
        )
        session.commit()

        # キャッシュを無効化
        gd._shop_listings_cache = None
        gd._cache_expires_at = None

        return _master_mobile_suit_to_dict(
            record, BlueprintService.settings_of(blueprint, record.price)
        )

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
        BlueprintService.delete_master_blueprint(
            session, BlueprintTargetType.MOBILE_SUIT, ms_id
        )
        session.commit()

        # キャッシュを無効化
        gd._shop_listings_cache = None
        gd._cache_expires_at = None

        return True
