#!/usr/bin/env python
"""マスターデータシードスクリプト.

JSON ディレクトリから master_mobile_suits / master_weapons / ace_pilots /
master_technologies / master_environments / master_theaters / master_blueprints
テーブルへデータを投入する。新しい環境の DB を作るときに使う。
べき等に実行可能（id が既に存在するレコードはスキップする）。

マスターの正本は DB である。投入元は次のどちらかにする。
- 本番から書き出したデータ（`scripts/maintenance/export_master_data.py` の出力。既定）
- テスト用の固定データ（`tests/fixtures/master/`）。値は本番と一致しない

`blueprints.json` が無いときは、新規に投入した機体・武器に標準配備の設計図マスターを作る。

Usage:
    python scripts/seed/seed_master_data.py [--data-dir DIR] [--force]

Options:
    --data-dir  投入元の JSON ディレクトリ。
                デフォルトは export_master_data.py の出力先。
    --force     既存レコードを上書きする（管理画面で変更済みのデータも上書き）。
                デフォルトは既存レコードをスキップ（管理画面変更を保護する）。
                本番 DB には使わない。

Environment:
    DATABASE_URL (または NEON_DATABASE_URL): 接続先データベースのURL
"""

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

# プロジェクトルートを Python パスに追加
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

# .env を読み込む（backend/.env）
load_dotenv(_ROOT / ".env")

from scripts.master_data import (  # noqa: E402
    ACE_PILOTS,
    BLUEPRINTS,
    ENVIRONMENTS,
    EXPORT_DIR,
    FIXTURE_DIR,
    MOBILE_SUITS,
    TECHNOLOGIES,
    THEATERS,
    WEAPONS,
    MasterData,
    read_master_dir,
)


def _get_engine():
    """DATABASE_URL 環境変数からエンジンを生成する."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("NEON_DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL または NEON_DATABASE_URL が設定されていません")
    return create_engine(url)


def _seed_by_id(
    session: Session, items: list[dict], model: type, force: bool
) -> tuple[list[str], int]:
    """各要素を id をキーにして model のテーブルへ投入する.

    Returns:
        tuple[list[str], int]: (挿入した id, スキップ件数)
    """
    inserted: list[str] = []
    skipped = 0
    for item in items:
        existing = session.get(model, item["id"])

        if existing is not None and not force:
            skipped += 1
            continue

        if existing is not None:
            for key, value in item.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.now(UTC)
            session.add(existing)
        else:
            session.add(model(**item))
            inserted.append(item["id"])
    return inserted, skipped


def _validate(data: MasterData) -> None:
    """列挙値と技術Lvの閾値を、DB に書く前に検証する."""
    from app.models.models import (
        ObstacleDensity,
        TerrainGrade,
        ViewerPreset,
        validate_level_thresholds,
    )

    for item in data[TECHNOLOGIES]:
        validate_level_thresholds(item["level_thresholds"])
    for item in data[ENVIRONMENTS]:
        ObstacleDensity(item["default_obstacle_density"])
        TerrainGrade(item["default_terrain_grade"])
        ViewerPreset(item["viewer_preset"])
    for item in data[THEATERS]:
        if item.get("obstacle_density") is not None:
            ObstacleDensity(item["obstacle_density"])


def _seed_blueprints(
    session: Session, items: list[dict], force: bool
) -> tuple[list[str], int]:
    """設計図マスターと必要な技術Lvを投入する.

    Returns:
        tuple[list[str], int]: (挿入した id, スキップ件数)
    """
    from app.models.models import MasterBlueprint, TechRequirement
    from app.services.technology_service import TechnologyService

    blueprints = [
        {k: v for k, v in item.items() if k != "tech_requirements"} for item in items
    ]
    inserted, skipped = _seed_by_id(session, blueprints, MasterBlueprint, force)
    session.flush()
    for item in items:
        if force or item["id"] in inserted:
            TechnologyService.replace_requirements(
                session,
                item["id"],
                [TechRequirement(**r) for r in item.get("tech_requirements", [])],
            )
    return inserted, skipped


def seed_session(session: Session, data: MasterData, force: bool) -> dict[str, int]:
    """マスターデータを session へ投入する。コミットは呼び出し側で行う.

    Returns:
        dict: 挿入/スキップ件数
    """
    from app.models.models import (
        AcePilot,
        BlueprintTargetType,
        MasterBlueprint,
        MasterEnvironment,
        MasterMobileSuit,
        MasterTechnology,
        MasterTheater,
        MasterWeapon,
    )
    from app.services.blueprint_service import BlueprintService

    _validate(data)
    result: dict[str, int] = {}

    def seed(name: str, model: type) -> list[str]:
        inserted, skipped = _seed_by_id(session, data[name], model, force)
        result[f"{name}_inserted"] = len(inserted)
        result[f"{name}_skipped"] = skipped
        # 後続のマスターが外部キーで参照するため、ここで書き込む。
        session.flush()
        return inserted

    seed(TECHNOLOGIES, MasterTechnology)
    seed(ENVIRONMENTS, MasterEnvironment)
    seed(THEATERS, MasterTheater)
    seed(ACE_PILOTS, AcePilot)
    new_suits = seed(MOBILE_SUITS, MasterMobileSuit)
    new_weapons = seed(WEAPONS, MasterWeapon)

    bp_inserted, bp_skipped = _seed_blueprints(session, data[BLUEPRINTS], force)
    prices = {
        (target_type, item["id"]): item["price"]
        for target_type, name in (
            (BlueprintTargetType.MOBILE_SUIT, MOBILE_SUITS),
            (BlueprintTargetType.WEAPON, WEAPONS),
        )
        for item in data[name]
    }
    # 練習機は設計図マスターを持たない
    trainer_ids = {item["id"] for item in data[MOBILE_SUITS] if item.get("is_trainer")}
    created_by_default = 0
    for target_type, ids in (
        (
            BlueprintTargetType.MOBILE_SUIT,
            [i for i in new_suits if i not in trainer_ids],
        ),
        (BlueprintTargetType.WEAPON, new_weapons),
    ):
        for target_id in ids:
            blueprint_id = BlueprintService.blueprint_id_for(target_type, target_id)
            if session.get(MasterBlueprint, blueprint_id) is None:
                created_by_default += 1
            BlueprintService.ensure_master_blueprint(
                session, target_type, target_id, prices[(target_type, target_id)]
            )
    result[f"{BLUEPRINTS}_inserted"] = len(bp_inserted) + created_by_default
    result[f"{BLUEPRINTS}_skipped"] = bp_skipped
    return result


def seed_master_data(data_dir: Path, force: bool = False) -> dict[str, int]:
    """data_dir の JSON を DB へ投入する.

    Args:
        data_dir: 投入元の JSON ディレクトリ
        force: True の場合、既存レコードを上書きする

    Returns:
        dict: 挿入/スキップ件数
    """
    from sqlmodel import SQLModel

    # create_all はインポート済みのモデルのテーブルだけを作る。
    import app.models.models  # noqa: F401

    data = read_master_dir(data_dir)
    engine = _get_engine()
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        result = seed_session(session, data, force)
        session.commit()
    return result


def main() -> None:
    """コマンドラインエントリーポイント."""
    parser = argparse.ArgumentParser(
        description=(
            "マスターデータ (mobile_suits / weapons / ace_pilots / technologies /"
            " environments / theaters / blueprints) を DB へシードする"
        )
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=EXPORT_DIR,
        help=(
            "投入元の JSON ディレクトリ（既定: export_master_data.py の出力先）。"
            f"本番に繋げない場合はテスト用データ {FIXTURE_DIR.relative_to(_ROOT)} を指定する"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="既存レコードを上書きする（デフォルトはスキップ）",
    )
    args = parser.parse_args()

    print(f"[INFO] シード開始 (data_dir={args.data_dir}, force={args.force})")
    try:
        result = seed_master_data(args.data_dir, force=args.force)
    except FileNotFoundError as exc:
        sys.exit(
            f"[ERROR] {exc}。先に export_master_data.py で書き出すか、"
            "--data-dir を指定してください。"
        )
    for name in (
        MOBILE_SUITS,
        WEAPONS,
        ACE_PILOTS,
        TECHNOLOGIES,
        ENVIRONMENTS,
        THEATERS,
        BLUEPRINTS,
    ):
        inserted = result[f"{name}_inserted"]
        skipped = result[f"{name}_skipped"]
        print(f"[INFO] {name}: {inserted} 件挿入, {skipped} 件スキップ")
    print("[INFO] シード完了")


if __name__ == "__main__":
    main()
