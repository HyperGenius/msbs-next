"""エースパイロットのマスターデータ管理サービス."""

import re
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.core import gamedata as gd
from app.core.npc_data import PERSONALITY_TYPES
from app.core.skills import get_skill_definition
from app.models.models import (
    ALL_PART_NAMES,
    AcePilot,
    AcePilotCreate,
    AcePilotMobileSuitSpec,
    AcePilotUpdate,
)


class AcePilotService:
    """エースパイロットのマスターデータ CRUD サービス."""

    @staticmethod
    def _to_raw(record: AcePilot) -> dict:
        """テーブルレコードを生JSON辞書に変換する."""
        return {
            "id": record.id,
            "name": record.name,
            "pilot_name": record.pilot_name,
            "description": record.description,
            "personality": record.personality,
            "mobile_suit": record.mobile_suit,
            "bounty_exp": record.bounty_exp,
            "bounty_credits": record.bounty_credits,
            "stats": record.stats,
            "skills": record.skills,
        }

    @staticmethod
    def _validate_personality(personality: str) -> None:
        if personality not in PERSONALITY_TYPES:
            raise ValueError(
                f"Invalid personality: '{personality}'. "
                f"Must be one of {PERSONALITY_TYPES}."
            )

    @staticmethod
    def _validate_mobile_suit(spec: AcePilotMobileSuitSpec) -> dict:
        """機体スペックを検証し、JSON列に保存する辞書形式に変換する."""
        if not spec.weapons:
            raise ValueError("mobile_suit.weapons must have at least one weapon.")
        invalid_parts = [p for p in spec.missing_parts if p not in ALL_PART_NAMES]
        if invalid_parts:
            raise ValueError(
                f"Invalid missing_parts: {invalid_parts}. "
                f"Must be any of {ALL_PART_NAMES}."
            )
        spec_dict = spec.model_dump()
        spec_dict["weapons"] = [w.model_dump() for w in spec.weapons]
        return spec_dict

    @staticmethod
    def _validate_skills(skills: dict[str, int]) -> None:
        for skill_id, level in skills.items():
            definition = get_skill_definition(skill_id)
            if definition is None:
                raise ValueError(f"Unknown skill id: '{skill_id}'.")
            if not 0 <= level <= definition["max_level"]:
                raise ValueError(
                    f"Skill '{skill_id}' level must be between 0 and "
                    f"{definition['max_level']}."
                )

    @staticmethod
    def get_ace_pilots(session: Session) -> list[dict]:
        """エースパイロットを全件返す（生JSON辞書形式）."""
        records = session.exec(select(AcePilot)).all()
        return [AcePilotService._to_raw(r) for r in records]

    @staticmethod
    def create_ace_pilot(session: Session, data: AcePilotCreate) -> dict:
        """エースパイロットを新規追加する.

        Raises:
            ValueError: id形式・性格・機体スペック・スキルが不正な場合
            LookupError: idが重複している場合
        """
        if not re.fullmatch(r"[a-z0-9_]+", data.id):
            raise ValueError(
                f"Invalid id format: '{data.id}'. Only lowercase alphanumeric and underscore are allowed."
            )
        AcePilotService._validate_personality(data.personality)
        mobile_suit = AcePilotService._validate_mobile_suit(data.mobile_suit)
        AcePilotService._validate_skills(data.skills)

        if session.get(AcePilot, data.id) is not None:
            raise LookupError(f"Ace pilot id '{data.id}' already exists.")

        record = AcePilot(
            id=data.id,
            name=data.name,
            pilot_name=data.pilot_name,
            description=data.description,
            personality=data.personality,
            mobile_suit=mobile_suit,
            bounty_exp=data.bounty_exp,
            bounty_credits=data.bounty_credits,
            stats=data.stats.model_dump(),
            skills=dict(data.skills),
        )
        session.add(record)
        session.commit()
        session.refresh(record)

        gd.invalidate_ace_pilots_cache()
        return AcePilotService._to_raw(record)

    @staticmethod
    def update_ace_pilot(
        session: Session, ace_id: str, data: AcePilotUpdate
    ) -> dict | None:
        """既存エースパイロットを更新する.

        Returns:
            dict | None: 更新後のデータ。見つからない場合はNone

        Raises:
            ValueError: 性格・機体スペック・スキルが不正な場合
        """
        record = session.get(AcePilot, ace_id)
        if record is None:
            return None

        update_dict = data.model_dump(exclude_unset=True)

        if update_dict.get("personality") is not None:
            AcePilotService._validate_personality(update_dict["personality"])
        if data.mobile_suit is not None:
            update_dict["mobile_suit"] = AcePilotService._validate_mobile_suit(
                data.mobile_suit
            )
        if data.skills is not None:
            AcePilotService._validate_skills(data.skills)

        for key, value in update_dict.items():
            # None は「未指定」と同義として扱い、NOT NULL 列を壊さない
            if value is not None:
                setattr(record, key, value)

        record.updated_at = datetime.now(UTC)
        session.add(record)
        session.commit()
        session.refresh(record)

        gd.invalidate_ace_pilots_cache()
        return AcePilotService._to_raw(record)

    @staticmethod
    def delete_ace_pilot(session: Session, ace_id: str) -> bool:
        """エースパイロットを削除する.

        生成済みの MobileSuit は ace_id 文字列で参照するのみのため削除は制限しない。
        参照先を失った機体は personality ベースのフォールバックで動作する。

        Returns:
            bool: 削除に成功した場合True、対象が存在しない場合False
        """
        record = session.get(AcePilot, ace_id)
        if record is None:
            return False

        session.delete(record)
        session.commit()

        gd.invalidate_ace_pilots_cache()
        return True
