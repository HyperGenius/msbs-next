"""マスターデータの書き出し（export_master_data）と投入（seed_master_data）のテスト."""

from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.db import json_serializer
from app.models.models import MasterBlueprint, TechRequirement
from app.services.technology_service import TechnologyService
from scripts.master_data import (
    BLUEPRINTS,
    FIXTURE_DIR,
    MASTER_NAMES,
    collect_master_data,
    read_master_dir,
    write_master_dir,
)
from scripts.seed.seed_master_data import seed_session


def _empty_engine() -> Engine:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        json_serializer=json_serializer,
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _seeded_engine() -> Engine:
    """テスト用データを投入し、設計図の設定を既定値から変えた DB を返す."""
    engine = _empty_engine()
    with Session(engine) as session:
        seed_session(session, read_master_dir(FIXTURE_DIR), force=False)
        blueprint = session.get(MasterBlueprint, "mobile_suit:dom")
        assert blueprint is not None
        blueprint.is_standard_issue = False
        blueprint.duplicate_credit_value = 777
        session.add(blueprint)
        TechnologyService.replace_requirements(
            session,
            blueprint.id,
            [TechRequirement(tech_id="beam_generator_tech", required_lv=2)],
        )
        session.commit()
    return engine


def test_exported_data_seeds_an_empty_database(tmp_path: Path) -> None:
    """書き出したデータを空の DB に投入すると、書き出し元と同じ内容になる."""
    with Session(_seeded_engine()) as session:
        exported = collect_master_data(session)
    write_master_dir(exported, tmp_path)

    target = _empty_engine()
    with Session(target) as session:
        seed_session(session, read_master_dir(tmp_path), force=False)
        session.commit()
    with Session(target) as session:
        assert collect_master_data(session) == exported

    blueprint = next(b for b in exported[BLUEPRINTS] if b["id"] == "mobile_suit:dom")
    assert blueprint["duplicate_credit_value"] == 777
    assert blueprint["tech_requirements"] == [
        {"tech_id": "beam_generator_tech", "required_lv": 2}
    ]


def test_seed_skips_existing_records() -> None:
    """--force なしの再投入は、既存のレコードを変えない."""
    engine = _seeded_engine()
    with Session(engine) as session:
        before = collect_master_data(session)
        data = read_master_dir(FIXTURE_DIR)
        result = seed_session(session, data, force=False)
        session.commit()
        assert collect_master_data(session) == before
    for name in MASTER_NAMES:
        assert result[f"{name}_inserted"] == 0
        assert result[f"{name}_skipped"] == len(data[name])


def test_seed_without_blueprints_creates_standard_issue() -> None:
    """blueprints.json が無いとき、機体・武器ごとに標準配備の設計図を作る."""
    data = read_master_dir(FIXTURE_DIR)
    assert data[BLUEPRINTS] == []
    with Session(_empty_engine()) as session:
        result = seed_session(session, data, force=False)
        session.commit()
        blueprints = collect_master_data(session)[BLUEPRINTS]
    assert len(blueprints) == len(data["mobile_suits"]) + len(data["weapons"])
    assert result[f"{BLUEPRINTS}_inserted"] == len(blueprints)
    assert all(b["is_standard_issue"] for b in blueprints)


def test_read_master_dir_requires_all_masters(tmp_path: Path) -> None:
    """6つのマスターの JSON が揃っていなければエラーにする."""
    write_master_dir({"mobile_suits": []}, tmp_path)
    with pytest.raises(FileNotFoundError):
        read_master_dir(tmp_path)
