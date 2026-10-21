"""機体マスターの EN（max_en / en_recovery）を、作成済みの機体へ同期する.

機体のスペックは購入・作成時に機体マスターからコピーされるため、
機体マスターの EN を変えても作成済みの ``mobile_suits`` は古い値のままになる。

コピー元は次の順に引く。
``master_mobile_suit_id`` が NULL の機体（練習機や、カラム追加前に購入した機体）があるため。

1. ``master_mobile_suit_id`` が指す機体マスター
2. 機体名が一致する機体マスター（地形適正・武器スロット数の解決と同じ）
3. 機体名が一致する練習機（``STARTER_KITS``。機体マスターに無い）

- プレイヤー機: 同期する
- NPC 機（``user_id`` が ``npc-`` で始まる）: 管理画面で機体ごとに調整するため、
  ``include_npc`` を指定したときだけ同期する
- エース機の雛形（``ace_pilots.mobile_suit``）: エース専用の値を持たせるため同期しない

EN は機体強化の対象ではないので、機体マスターの値でそのまま上書きしてよい。
"""

from collections import Counter
from dataclasses import dataclass, field

from sqlmodel import Session, col, select

from app.core.gamedata import STARTER_KITS
from app.models.models import MasterMobileSuit, MasterMobileSuitSpec, MobileSuit

SYNCABLE_FIELDS: tuple[str, ...] = ("max_en", "en_recovery")

NPC_USER_ID_PREFIX = "npc-"

TARGET_PLAYER = "mobile_suits（プレイヤー機）"
TARGET_NPC = "mobile_suits（NPC機）"
TARGET_NPC_SKIPPED = "mobile_suits（NPC機・対象外）"


@dataclass
class MobileSuitEnSyncReport:
    """同期で変わる（変わった）値の集計."""

    # (同期先, コピー元ID, フィールド, 変更前, 変更後) → 件数
    changes: Counter[tuple[str, str, str, int, int]] = field(default_factory=Counter)
    # 同期先 → 更新した行数
    updated_rows: Counter[str] = field(default_factory=Counter)

    @property
    def has_changes(self) -> bool:
        """更新する行が1つでもあるか."""
        return any(
            target != TARGET_NPC_SKIPPED and count > 0
            for target, count in self.updated_rows.items()
        )


@dataclass
class _Sources:
    """コピー元の EN."""

    # コピー元ID（機体マスターID または練習機ID） → フィールド → 値
    values: dict[str, dict[str, int]]
    # 機体名 → コピー元ID
    ids_by_name: dict[str, str]


def _en_values(specs: dict) -> dict[str, int]:
    # specs にキーが無いものは既定値として扱う（バトルで使われる値と同じ）
    return {
        name: specs.get(name, MasterMobileSuitSpec.model_fields[name].get_default())
        for name in SYNCABLE_FIELDS
    }


def _load_sources(session: Session, source_ids: list[str] | None) -> _Sources:
    values: dict[str, dict[str, int]] = {}
    ids_by_name: dict[str, str] = {}
    for kit in STARTER_KITS.values():
        if not source_ids or kit["id"] in source_ids:
            values[kit["id"]] = _en_values(kit["specs"])
            ids_by_name[kit["name"]] = kit["id"]

    stmt = select(MasterMobileSuit)
    if source_ids:
        stmt = stmt.where(col(MasterMobileSuit.id).in_(source_ids))
    # 機体名が練習機と重なったときは機体マスターを優先する
    for mms in session.exec(stmt).all():
        values[mms.id] = _en_values(mms.specs or {})
        ids_by_name[mms.name] = mms.id

    missing = sorted(set(source_ids or []) - values.keys())
    if missing:
        raise ValueError(f"機体マスター・練習機に無いIDです: {', '.join(missing)}")
    return _Sources(values=values, ids_by_name=ids_by_name)


def _source_id(ms: MobileSuit, sources: _Sources) -> str | None:
    if ms.master_mobile_suit_id is not None:
        return (
            ms.master_mobile_suit_id
            if ms.master_mobile_suit_id in sources.values
            else None
        )
    return sources.ids_by_name.get(ms.name)


def _target(ms: MobileSuit) -> str | None:
    if ms.user_id is None:
        # マッチング時に作られるエース機のコピーなど。編集対象にしない
        return None
    if ms.user_id.startswith(NPC_USER_ID_PREFIX):
        return TARGET_NPC
    return TARGET_PLAYER


def sync_mobile_suit_en(
    session: Session,
    master_ids: list[str] | None = None,
    include_npc: bool = False,
) -> MobileSuitEnSyncReport:
    """機体マスター・練習機の EN を作成済みの機体へ反映し、変わった値を返す.

    master_ids には機体マスターIDと練習機IDを指定できる。None なら全件を対象にする。
    commit はしない。呼び出し元が結果を見て commit か rollback を選ぶ。
    """
    report = MobileSuitEnSyncReport()

    with session.no_autoflush:
        sources = _load_sources(session, master_ids)
        if not sources.values:
            return report

        stmt = select(MobileSuit).where(
            col(MobileSuit.master_mobile_suit_id).in_(list(sources.values))
            | (
                col(MobileSuit.master_mobile_suit_id).is_(None)
                & col(MobileSuit.name).in_(list(sources.ids_by_name))
            )
        )
        for ms in session.exec(stmt).all():
            target = _target(ms)
            source_id = _source_id(ms, sources)
            if target is None or source_id is None:
                continue
            diffs = {
                name: (getattr(ms, name), new)
                for name, new in sources.values[source_id].items()
                if getattr(ms, name) != new
            }
            if not diffs:
                continue
            if target == TARGET_NPC and not include_npc:
                target = TARGET_NPC_SKIPPED
            else:
                for name, (_, new) in diffs.items():
                    setattr(ms, name, new)
                session.add(ms)
            for name, (old, new) in diffs.items():
                report.changes[(target, source_id, name, old, new)] += 1
            report.updated_rows[target] += 1

    return report
