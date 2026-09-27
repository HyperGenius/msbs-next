"""技術断片の付与と、技術Lvの計算・技術マスターの管理を行うサービス."""

import re
from bisect import bisect_right
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlmodel import Session, col, delete, select

from app.models.models import (
    BlueprintTechRequirement,
    DropTableEntry,
    MasterTechnology,
    MasterTechnologyCreate,
    MasterTechnologyEntry,
    MasterTechnologyUpdate,
    Pilot,
    PlayerTechnology,
    TechRequirement,
)

TECH_ID_PATTERN = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True)
class TechProgress:
    """累計断片数から求めた技術Lvの進捗."""

    level: int
    max_level: int
    next_level_threshold: int | None
    fragments_to_next_level: int | None


@dataclass(frozen=True)
class TechFragmentGrantResult:
    """技術断片の付与結果."""

    tech_id: str
    fragment_count: int
    progress: TechProgress
    is_level_up: bool
    credits_awarded: int


class TechnologyService:
    """技術サービス."""

    @staticmethod
    def level_for(thresholds: Sequence[int], fragment_count: int) -> int:
        """累計断片数に対応する技術Lvを返す。閾値は狭義単調増加が前提."""
        return bisect_right(thresholds, fragment_count)

    @staticmethod
    def progress(thresholds: Sequence[int], fragment_count: int) -> TechProgress:
        """累計断片数から技術Lvと次のLvまでの残りを求める."""
        level = TechnologyService.level_for(thresholds, fragment_count)
        max_level = len(thresholds)
        if level >= max_level:
            return TechProgress(
                level=level,
                max_level=max_level,
                next_level_threshold=None,
                fragments_to_next_level=None,
            )
        next_threshold = thresholds[level]
        return TechProgress(
            level=level,
            max_level=max_level,
            next_level_threshold=next_threshold,
            fragments_to_next_level=next_threshold - fragment_count,
        )

    @staticmethod
    def fragment_counts(session: Session, user_id: str) -> dict[str, int]:
        """プレイヤーの技術IDごとの累計断片数を返す。未入手の技術は含めない."""
        return dict(
            session.exec(
                select(PlayerTechnology.tech_id, PlayerTechnology.fragment_count).where(
                    PlayerTechnology.user_id == user_id
                )
            ).all()
        )

    @staticmethod
    def levels_by_tech(session: Session, user_id: str) -> dict[str, int]:
        """プレイヤーの技術IDごとの技術Lvを返す。未入手の技術は含めない."""
        rows = session.exec(
            select(
                PlayerTechnology.tech_id,
                PlayerTechnology.fragment_count,
                MasterTechnology.level_thresholds,
            )
            .join(
                MasterTechnology,
                col(MasterTechnology.id) == col(PlayerTechnology.tech_id),
            )
            .where(PlayerTechnology.user_id == user_id)
        ).all()
        return {
            tech_id: TechnologyService.level_for(thresholds, count)
            for tech_id, count, thresholds in rows
        }

    @staticmethod
    def grant_fragment(
        session: Session, user_id: str, tech_id: str
    ) -> TechFragmentGrantResult:
        """プレイヤーに技術断片を1個付与する.

        最大Lvに達していれば累計数に加算せず、換金額分のクレジットを加算する。
        コミットは呼び出し側で行う。

        Raises:
            LookupError: 技術マスターが無い場合。
                または最大Lvで、クレジットを加算するパイロットが無い場合。
        """
        tech = session.get(MasterTechnology, tech_id)
        if tech is None:
            raise LookupError(f"Technology '{tech_id}' not found.")

        owned = session.exec(
            select(PlayerTechnology).where(
                PlayerTechnology.user_id == user_id,
                PlayerTechnology.tech_id == tech_id,
            )
        ).first()
        count_before = owned.fragment_count if owned else 0
        before = TechnologyService.progress(tech.level_thresholds, count_before)

        if before.level >= before.max_level:
            pilot = session.exec(select(Pilot).where(Pilot.user_id == user_id)).first()
            if pilot is None:
                raise LookupError(f"Pilot for user '{user_id}' not found.")
            pilot.credits += tech.overflow_credit_value
            pilot.updated_at = datetime.now(UTC)
            session.add(pilot)
            return TechFragmentGrantResult(
                tech_id=tech_id,
                fragment_count=count_before,
                progress=before,
                is_level_up=False,
                credits_awarded=tech.overflow_credit_value,
            )

        if owned is None:
            owned = PlayerTechnology(user_id=user_id, tech_id=tech_id)
        owned.fragment_count = count_before + 1
        owned.updated_at = datetime.now(UTC)
        session.add(owned)
        after = TechnologyService.progress(tech.level_thresholds, owned.fragment_count)
        return TechFragmentGrantResult(
            tech_id=tech_id,
            fragment_count=owned.fragment_count,
            progress=after,
            is_level_up=after.level > before.level,
            credits_awarded=0,
        )

    # --- 購入条件 ---

    @staticmethod
    def validate_requirements(
        session: Session, requirements: Sequence[TechRequirement]
    ) -> None:
        """必要な技術Lvの設定を検証する.

        Raises:
            ValueError: 同じ技術が2つ以上ある場合。技術マスターに無い技術がある場合。
                または必要Lvが技術の最大Lvを超える場合。
        """
        duplicated = sorted(
            tech_id
            for tech_id, count in Counter(r.tech_id for r in requirements).items()
            if count > 1
        )
        if duplicated:
            raise ValueError(f"Duplicate tech requirements: {', '.join(duplicated)}")

        thresholds_by_tech = dict(
            session.exec(
                select(MasterTechnology.id, MasterTechnology.level_thresholds).where(
                    col(MasterTechnology.id).in_([r.tech_id for r in requirements])
                )
            ).all()
        )
        missing = sorted({r.tech_id for r in requirements} - set(thresholds_by_tech))
        if missing:
            raise ValueError(f"Technologies not found: {', '.join(missing)}")

        for requirement in requirements:
            max_level = len(thresholds_by_tech[requirement.tech_id])
            if requirement.required_lv > max_level:
                raise ValueError(
                    f"required_lv of '{requirement.tech_id}' must be ≤ {max_level}."
                )

    @staticmethod
    def replace_requirements(
        session: Session, blueprint_id: str, requirements: Sequence[TechRequirement]
    ) -> None:
        """設計図の必要な技術Lvを置き換える。コミットは呼び出し側で行う.

        Raises:
            ValueError: `validate_requirements` と同じ。
        """
        TechnologyService.validate_requirements(session, requirements)
        session.exec(  # type: ignore[call-overload]
            delete(BlueprintTechRequirement).where(
                col(BlueprintTechRequirement.blueprint_id) == blueprint_id
            )
        )
        for requirement in requirements:
            session.add(
                BlueprintTechRequirement(
                    blueprint_id=blueprint_id,
                    tech_id=requirement.tech_id,
                    required_lv=requirement.required_lv,
                )
            )

    @staticmethod
    def requirements_by_blueprint(
        session: Session, blueprint_ids: Sequence[str] | None = None
    ) -> dict[str, list[TechRequirement]]:
        """設計図IDごとの必要な技術Lvを、技術ID順に返す.

        `blueprint_ids` が None なら全設計図を対象にする。
        """
        statement = select(BlueprintTechRequirement).order_by(
            col(BlueprintTechRequirement.blueprint_id),
            col(BlueprintTechRequirement.tech_id),
        )
        if blueprint_ids is not None:
            statement = statement.where(
                col(BlueprintTechRequirement.blueprint_id).in_(blueprint_ids)
            )
        requirements: dict[str, list[TechRequirement]] = {}
        for row in session.exec(statement).all():
            requirements.setdefault(row.blueprint_id, []).append(
                TechRequirement(tech_id=row.tech_id, required_lv=row.required_lv)
            )
        return requirements

    @staticmethod
    def tech_names(
        session: Session, tech_ids: Sequence[str] | None = None
    ) -> dict[str, str]:
        """技術IDごとの表示名を返す.

        `tech_ids` が None なら全技術を対象にする。
        """
        statement = select(MasterTechnology.id, MasterTechnology.name)
        if tech_ids is not None:
            if not tech_ids:
                return {}
            statement = statement.where(col(MasterTechnology.id).in_(tech_ids))
        return dict(session.exec(statement).all())

    # --- 技術マスターの管理 ---

    @staticmethod
    def list_technologies(session: Session) -> list[MasterTechnology]:
        """技術マスターを技術ID順に返す."""
        return list(
            session.exec(
                select(MasterTechnology).order_by(col(MasterTechnology.id))
            ).all()
        )

    @staticmethod
    def to_entry(tech: MasterTechnology) -> MasterTechnologyEntry:
        """技術マスターを管理者用レスポンスにする."""
        return MasterTechnologyEntry(
            id=tech.id,
            name=tech.name,
            description=tech.description,
            level_thresholds=list(tech.level_thresholds),
            overflow_credit_value=tech.overflow_credit_value,
        )

    @staticmethod
    def create_technology(
        session: Session, data: MasterTechnologyCreate
    ) -> MasterTechnology:
        """技術マスターを追加する.

        Raises:
            ValueError: IDの形式が不正な場合。
            LookupError: IDが重複している場合。
        """
        if not TECH_ID_PATTERN.fullmatch(data.id):
            raise ValueError(
                f"Invalid id format: '{data.id}'. "
                "Only lowercase alphanumeric and underscore are allowed."
            )
        if session.get(MasterTechnology, data.id) is not None:
            raise LookupError(f"Technology id '{data.id}' already exists.")

        tech = MasterTechnology(
            id=data.id,
            name=data.name,
            description=data.description,
            level_thresholds=list(data.level_thresholds),
            overflow_credit_value=data.overflow_credit_value,
        )
        session.add(tech)
        session.commit()
        session.refresh(tech)
        return tech

    @staticmethod
    def update_technology(
        session: Session, tech_id: str, data: MasterTechnologyUpdate
    ) -> MasterTechnology | None:
        """技術マスターを更新する.

        閾値を減らして最大Lvが下がっても、それを超える必要Lvの設定は残す。
        その設計図は購入できなくなるため、ValueError にする。

        Returns:
            更新後の技術マスター。見つからなければ None。

        Raises:
            ValueError: 新しい最大Lvを超える必要Lvを設定した設計図がある場合。
        """
        tech = session.get(MasterTechnology, tech_id)
        if tech is None:
            return None

        updates = data.model_dump(exclude_unset=True, exclude_none=True)
        if "level_thresholds" in updates:
            max_level = len(updates["level_thresholds"])
            too_high = session.exec(
                select(BlueprintTechRequirement.blueprint_id).where(
                    BlueprintTechRequirement.tech_id == tech_id,
                    col(BlueprintTechRequirement.required_lv) > max_level,
                )
            ).all()
            if too_high:
                raise ValueError(
                    f"Blueprints require a level above {max_level}: "
                    f"{', '.join(sorted(too_high))}"
                )

        for key, value in updates.items():
            setattr(tech, key, value)
        tech.updated_at = datetime.now(UTC)
        session.add(tech)
        session.commit()
        session.refresh(tech)
        return tech

    @staticmethod
    def delete_technology(session: Session, tech_id: str) -> bool:
        """技術マスターと、プレイヤーの累計断片数を削除する.

        Returns:
            削除したら True。見つからなければ False。

        Raises:
            LookupError: 設計図の購入条件かドロップテーブルから参照されている場合。
        """
        tech = session.get(MasterTechnology, tech_id)
        if tech is None:
            return False

        blueprint_ids = session.exec(
            select(BlueprintTechRequirement.blueprint_id).where(
                BlueprintTechRequirement.tech_id == tech_id
            )
        ).all()
        if blueprint_ids:
            raise LookupError(
                f"Technology '{tech_id}' is required by blueprints: "
                f"{', '.join(sorted(blueprint_ids))}"
            )
        in_drop_table = session.exec(
            select(DropTableEntry.id).where(DropTableEntry.tech_id == tech_id)
        ).first()
        if in_drop_table is not None:
            raise LookupError(f"Technology '{tech_id}' is in a drop table.")

        session.exec(  # type: ignore[call-overload]
            delete(PlayerTechnology).where(col(PlayerTechnology.tech_id) == tech_id)
        )
        session.delete(tech)
        session.commit()
        return True
