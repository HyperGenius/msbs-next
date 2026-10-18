"""武器マスターの値を、武器スペックのコピーを持つデータへ同期する.

武器スペックは参照ではなくコピーで持たれているため、武器マスターを変えても
次の場所は古いままになる。

- ``player_weapons.base_snapshot``（購入した武器）
- ``mobile_suits.weapons`` の購入した武器のスロット（``resync_mobile_suit_weapons`` で作り直す）
- ``mobile_suits.weapons`` の初期装備のスロット（``player_weapons`` の行が無い）
- ``master_mobile_suits.specs.weapons``（機体の購入・作成時のコピー元）

エースパイロットの武器は武器マスターとの対応付けが保証されないため更新せず、
差分の件数だけを数える。
"""

import json
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import attributes
from sqlmodel import Session, col, select

from app.models.models import (
    AcePilot,
    MasterMobileSuit,
    MasterWeapon,
    MasterWeaponSpec,
    MobileSuit,
    PlayerWeapon,
    WeaponSpecBase,
)
from app.services.engineering_service import EngineeringService
from app.services.weapon_service import WeaponService

TARGET_BASE_SNAPSHOT = "player_weapons.base_snapshot"
TARGET_PURCHASED_SLOT = "mobile_suits.weapons（購入した武器）"
TARGET_INITIAL_SLOT = "mobile_suits.weapons（初期装備）"
TARGET_MASTER_MOBILE_SUIT = "master_mobile_suits.specs.weapons"
TARGET_ACE_PILOT = "ace_pilots（対象外・更新しない）"

# id / master_weapon_id は対応付けのキーなので同期しない。
SYNCABLE_FIELDS: tuple[str, ...] = ("name", *WeaponSpecBase.model_fields)

_MISSING_REQUIRED = object()


@dataclass
class WeaponMasterSyncReport:
    """同期で変わる（変わった）値の集計."""

    # (同期先, 武器ID, フィールド, 変更前, 変更後) → 件数
    changes: Counter[tuple[str, str, str, str, str]] = field(default_factory=Counter)
    # 同期先 → 更新した行数
    updated_rows: Counter[str] = field(default_factory=Counter)

    @property
    def has_changes(self) -> bool:
        """更新する行が1つでもあるか."""
        return any(
            target != TARGET_ACE_PILOT and count > 0
            for target, count in self.updated_rows.items()
        )

    def record(
        self, target: str, weapon_id: str, diffs: dict[str, tuple[Any, Any]]
    ) -> None:
        """1件のコピーで変わる値を数える."""
        for name, (old, new) in diffs.items():
            self.changes[(target, weapon_id, name, _fmt(old), _fmt(new))] += 1


def _fmt(value: Any) -> str:
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is _MISSING_REQUIRED:
        return "(未設定)"
    return str(value)


def _field_default(name: str) -> Any:
    info = WeaponSpecBase.model_fields.get(name)
    if info is None or info.is_required():
        return _MISSING_REQUIRED
    return info.get_default(call_default_factory=True)


def _as_dict(weapon: Any) -> dict:
    # resync 後の MobileSuit.weapons には Weapon オブジェクトが入る。
    if hasattr(weapon, "model_dump"):
        return weapon.model_dump()
    return dict(weapon or {})


def _effective_value(weapon: dict, name: str) -> Any:
    # 機体マスターの武器は既定値のキーを省いて保存されているため、キーが無ければ既定値として比べる。
    return weapon[name] if name in weapon else _field_default(name)


def _diff(
    weapon: dict, source: dict, fields: tuple[str, ...]
) -> dict[str, tuple[Any, Any]]:
    diffs: dict[str, tuple[Any, Any]] = {}
    for name in fields:
        old = _effective_value(weapon, name)
        new = _effective_value(source, name)
        if old != new:
            diffs[name] = (old, new)
    return diffs


def _apply(weapon: dict, diffs: dict[str, tuple[Any, Any]]) -> dict:
    return {**weapon, **{name: new for name, (_, new) in diffs.items()}}


def _master_weapon_id(weapon: dict) -> str | None:
    return weapon.get("master_weapon_id") or weapon.get("id")


def validate_fields(fields: list[str] | None) -> tuple[str, ...]:
    """同期するフィールドを検証して返す。None なら全フィールド."""
    if not fields:
        return SYNCABLE_FIELDS
    unknown = [name for name in fields if name not in SYNCABLE_FIELDS]
    if unknown:
        raise ValueError(
            f"同期できないフィールドです: {', '.join(unknown)}"
            f"（指定できるもの: {', '.join(SYNCABLE_FIELDS)}）"
        )
    return tuple(fields)


def _load_masters(session: Session, weapon_ids: list[str] | None) -> dict[str, dict]:
    stmt = select(MasterWeapon)
    if weapon_ids:
        stmt = stmt.where(col(MasterWeapon.id).in_(weapon_ids))
    masters = {
        mw.id: {"name": mw.name, **MasterWeaponSpec(**mw.weapon).model_dump()}
        for mw in session.exec(stmt).all()
    }
    missing = sorted(set(weapon_ids or []) - masters.keys())
    if missing:
        raise ValueError(f"武器マスターに無いIDです: {', '.join(missing)}")
    return masters


def sync_weapon_master(
    session: Session,
    weapon_ids: list[str] | None = None,
    fields: list[str] | None = None,
) -> WeaponMasterSyncReport:
    """武器マスターの値をコピー先へ反映し、変わった値を返す.

    commit はしない。呼び出し元が結果を見て commit か rollback を選ぶ。
    autoflush を止めているので、commit するまで DB には書き込まれない。
    """
    sync_fields = validate_fields(fields)
    report = WeaponMasterSyncReport()

    with session.no_autoflush:
        masters = _load_masters(session, weapon_ids)
        if not masters:
            return report

        resync_ms_ids = _sync_base_snapshots(session, masters, sync_fields, report)
        _sync_initial_slots(session, masters, sync_fields, report)
        _resync_purchased_slots(session, resync_ms_ids, report)
        _sync_master_mobile_suits(session, masters, sync_fields, report)
        _count_ace_pilot_diffs(session, masters, sync_fields, report)

    return report


def _sync_base_snapshots(
    session: Session,
    masters: dict[str, dict],
    fields: tuple[str, ...],
    report: WeaponMasterSyncReport,
) -> set[uuid.UUID]:
    """base_snapshot を更新し、作り直しが必要な機体のIDを返す.

    custom_stats（武器改造の差分）は触らない。
    """
    resync_ms_ids: set[uuid.UUID] = set()
    stmt = select(PlayerWeapon).where(
        col(PlayerWeapon.master_weapon_id).in_(list(masters))
    )
    for pw in session.exec(stmt).all():
        snapshot = dict(pw.base_snapshot or {})
        diffs = _diff(snapshot, masters[pw.master_weapon_id], fields)
        if not diffs:
            continue
        pw.base_snapshot = _apply(snapshot, diffs)
        attributes.flag_modified(pw, "base_snapshot")
        session.add(pw)
        report.record(TARGET_BASE_SNAPSHOT, pw.master_weapon_id, diffs)
        report.updated_rows[TARGET_BASE_SNAPSHOT] += 1
        if pw.equipped_ms_id is not None:
            resync_ms_ids.add(pw.equipped_ms_id)
    return resync_ms_ids


def _with_power_bonus(master: dict, ms: MobileSuit) -> dict:
    power = EngineeringService.add_weapon_power_bonus(
        master["power"], ms.weapon_power_bonus or 0
    )
    return {**master, "power": power}


def _sync_initial_slots(
    session: Session,
    masters: dict[str, dict],
    fields: tuple[str, ...],
    report: WeaponMasterSyncReport,
) -> None:
    """player_weapons の行が無いスロット（初期装備）をマスターの値で上書きする.

    初期装備は改造できないものとして扱う。power はマスターの値に、
    機体強化の加算値（weapon_power_bonus）を足した値にする。
    """
    purchased_slots = {
        (pw.equipped_ms_id, pw.equipped_slot)
        for pw in session.exec(
            select(PlayerWeapon).where(col(PlayerWeapon.equipped_ms_id).is_not(None))
        ).all()
    }
    for ms in session.exec(select(MobileSuit)).all():
        new_weapons: list[Any] = []
        changed = False
        for slot_index, raw in enumerate(ms.weapons or []):
            weapon = _as_dict(raw)
            weapon_id = _master_weapon_id(weapon)
            if (
                (ms.id, slot_index) in purchased_slots
                or weapon_id is None
                or weapon_id not in masters
            ):
                new_weapons.append(raw)
                continue
            diffs = _diff(weapon, _with_power_bonus(masters[weapon_id], ms), fields)
            if not diffs:
                new_weapons.append(raw)
                continue
            new_weapons.append(_apply(weapon, diffs))
            report.record(TARGET_INITIAL_SLOT, weapon_id, diffs)
            changed = True
        if changed:
            ms.weapons = new_weapons
            attributes.flag_modified(ms, "weapons")
            session.add(ms)
            report.updated_rows[TARGET_INITIAL_SLOT] += 1


def _resync_purchased_slots(
    session: Session,
    ms_ids: set[uuid.UUID],
    report: WeaponMasterSyncReport,
) -> None:
    """購入した武器のスロットを base_snapshot + custom_stats から作り直す.

    バトルエントリー時と同じ resync を使う。そのため同期対象のフィールド以外も、
    エントリー時に変わるはずだった値（未反映の改造など）はここで変わる。
    """
    for ms_id in ms_ids:
        ms = session.get(MobileSuit, ms_id)
        if ms is None:
            continue
        before = [_as_dict(w) for w in ms.weapons or []]
        WeaponService.resync_mobile_suit_weapons(session, ms)
        after = [_as_dict(w) for w in ms.weapons or []]
        changed = False
        for old, new in zip(before, after, strict=True):
            diffs = _diff(old, new, SYNCABLE_FIELDS)
            if diffs:
                report.record(
                    TARGET_PURCHASED_SLOT, _master_weapon_id(new) or "?", diffs
                )
                changed = True
        if changed:
            session.add(ms)
            report.updated_rows[TARGET_PURCHASED_SLOT] += 1


def _sync_master_mobile_suits(
    session: Session,
    masters: dict[str, dict],
    fields: tuple[str, ...],
    report: WeaponMasterSyncReport,
) -> None:
    """機体マスターの specs.weapons を更新する。これから作られる機体のコピー元になる."""
    for mms in session.exec(select(MasterMobileSuit)).all():
        specs = dict(mms.specs or {})
        new_weapons = []
        changed = False
        for weapon in specs.get("weapons", []):
            weapon_id = _master_weapon_id(weapon)
            if weapon_id is None or weapon_id not in masters:
                new_weapons.append(weapon)
                continue
            diffs = _diff(weapon, masters[weapon_id], fields)
            if diffs:
                weapon = _apply(weapon, diffs)
                report.record(TARGET_MASTER_MOBILE_SUIT, weapon_id, diffs)
                changed = True
            new_weapons.append(weapon)
        if changed:
            mms.specs = {**specs, "weapons": new_weapons}
            attributes.flag_modified(mms, "specs")
            session.add(mms)
            report.updated_rows[TARGET_MASTER_MOBILE_SUIT] += 1


def _count_ace_pilot_diffs(
    session: Session,
    masters: dict[str, dict],
    fields: tuple[str, ...],
    report: WeaponMasterSyncReport,
) -> None:
    for ace in session.exec(select(AcePilot)).all():
        has_diff = False
        for weapon in (ace.mobile_suit or {}).get("weapons", []):
            weapon_id = _master_weapon_id(weapon)
            if weapon_id is None or weapon_id not in masters:
                continue
            diffs = _diff(weapon, masters[weapon_id], fields)
            if diffs:
                report.record(TARGET_ACE_PILOT, weapon_id, diffs)
                has_diff = True
        if has_diff:
            report.updated_rows[TARGET_ACE_PILOT] += 1
