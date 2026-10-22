"""マスターデータの JSON ディレクトリと DB の読み書き.

マスターの正本は DB である。JSON ディレクトリは、DB から書き出したデータか、
テスト用の固定データ（`tests/fixtures/master/`）のどちらかになる。

`app` は関数の中で import する。読み取り専用の接続を使う前に
`app.db` のエンジンが作られると、書き込み可能な接続になるため。
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlmodel import Session

BACKEND_DIR = Path(__file__).resolve().parent.parent
FIXTURE_DIR = BACKEND_DIR / "tests" / "fixtures" / "master"
EXPORT_DIR = BACKEND_DIR / "scripts" / "maintenance" / "output" / "master_data"

MOBILE_SUITS = "mobile_suits"
WEAPONS = "weapons"
ACE_PILOTS = "ace_pilots"
TECHNOLOGIES = "technologies"
ENVIRONMENTS = "environments"
THEATERS = "theaters"
BLUEPRINTS = "blueprints"

MASTER_NAMES: tuple[str, ...] = (
    MOBILE_SUITS,
    WEAPONS,
    ACE_PILOTS,
    TECHNOLOGIES,
    ENVIRONMENTS,
    THEATERS,
)

# 投入時に DB が値を決める列。書き出しても投入に使わない。
_TIMESTAMP_COLUMNS = {"created_at", "updated_at"}

MasterData = dict[str, list[dict]]


def read_master_dir(data_dir: Path) -> MasterData:
    """ディレクトリの JSON を読み、マスター名ごとの要素のリストを返す.

    `blueprints.json` は任意とする。無ければ空のリストにする。

    Raises:
        FileNotFoundError: 6つのマスターの JSON のどれかが無い場合
    """
    data: MasterData = {}
    for name in MASTER_NAMES:
        path = data_dir / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"{path} が見つかりません")
        data[name] = json.loads(path.read_text(encoding="utf-8"))
    blueprints_path = data_dir / f"{BLUEPRINTS}.json"
    data[BLUEPRINTS] = (
        json.loads(blueprints_path.read_text(encoding="utf-8"))
        if blueprints_path.exists()
        else []
    )
    return data


def write_master_dir(data: MasterData, out_dir: Path) -> list[Path]:
    """マスター名ごとに JSON を書き出し、書いたファイルのパスを返す."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, items in data.items():
        path = out_dir / f"{name}.json"
        path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        paths.append(path)
    return paths


def collect_master_data(session: "Session") -> MasterData:
    """DB の6つのマスターと設計図マスターを、`read_master_dir` と同じ形で返す.

    要素は id 順に並べる。書き出したファイルの差分を見やすくするため。
    """
    from sqlmodel import col, select

    from app.models.models import (
        AcePilot,
        MasterBlueprint,
        MasterEnvironment,
        MasterMobileSuit,
        MasterTechnology,
        MasterTheater,
        MasterWeapon,
    )
    from app.services.technology_service import TechnologyService

    def rows(model: type) -> list[dict]:
        # model_dump のキー順は読み込み方で変わる。列の定義順にそろえる。
        columns = [c for c in model.model_fields if c not in _TIMESTAMP_COLUMNS]
        records = session.exec(select(model).order_by(col(model.id))).all()
        return [{c: getattr(r, c) for c in columns} for r in records]

    requirements = TechnologyService.requirements_by_blueprint(session)
    blueprints = [
        {
            **blueprint,
            "tech_requirements": [
                r.model_dump() for r in requirements.get(blueprint["id"], [])
            ],
        }
        for blueprint in rows(MasterBlueprint)
    ]
    return {
        MOBILE_SUITS: rows(MasterMobileSuit),
        WEAPONS: rows(MasterWeapon),
        ACE_PILOTS: rows(AcePilot),
        TECHNOLOGIES: rows(MasterTechnology),
        ENVIRONMENTS: rows(MasterEnvironment),
        THEATERS: rows(MasterTheater),
        BLUEPRINTS: blueprints,
    }


def load_master_data_from_readonly_db() -> MasterData:
    """本番 DB に読み取り専用で接続し、`collect_master_data` の結果を返す.

    `app.db` より先に呼ぶこと。

    Raises:
        ReadOnlyConfigError: 読み取り専用の接続を用意できない場合
    """
    from sqlmodel import Session

    from scripts.simulation.local_sim.readonly_db import (
        assert_read_only_session,
        use_readonly_database,
    )

    use_readonly_database()
    from app.db import engine

    assert_read_only_session(engine)
    with Session(engine) as session:
        return collect_master_data(session)


def load_master_data(data_dir: Path | None) -> MasterData:
    """`data_dir` の JSON を読む。None なら本番 DB を読み取り専用で読む."""
    if data_dir is None:
        return load_master_data_from_readonly_db()
    return read_master_dir(data_dir)
