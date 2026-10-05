"""ローカルシミュレータの run（ロスターからの実行と世代管理）のテスト."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlmodel import Session

import app
import app.db as app_db
from app.core import gamedata
from app.core.gamedata import get_ace_pilots
from app.engine.rng import new_numpy_rng
from scripts.simulation.local_sim import run as local_run
from scripts.simulation.local_sim.fetch import FetchOptions, UnitSpec, build_roster
from scripts.simulation.local_sim.generations import (
    MANIFEST_FILE,
    ROSTER_FILE,
    BattleRecord,
    find_generation,
    list_generations,
    read_manifest,
    set_pinned,
)
from scripts.simulation.local_sim.roster import Roster, load_roster, save_roster
from scripts.simulation.local_sim.run import (
    OfflineDatabaseError,
    RunOptions,
    player_entry_index,
    run_generation,
)
from tests.unit.test_local_sim_fetch import _npc, _player

# ログの一致を確かめるには決着前でも十分なため、短く打ち切って時間を抑える。
_SHORT_STEPS = 150
_BASE_TIME = datetime(2026, 10, 5, 21, 30, 0).astimezone()


@pytest.fixture(name="roster_path")
def roster_path_fixture(session: Session, tmp_path: Path) -> Path:
    """プレイヤー1機・NPC・エース・戦域入りのロスターを保存する."""
    player = _player(session, "user_a")
    _npc(session, "npc-1")
    with Session(app_db.engine, autoflush=False) as fetch_session:
        roster = build_roster(
            fetch_session,
            FetchOptions(
                pilots=[UnitSpec(str(player.id))],
                npc_count=2,
                ace_count=1,
                theater_id="solomon",
            ),
            "run_test",
        )
    return save_roster(roster, rosters_dir=tmp_path / "rosters")


@pytest.fixture(name="generations_dir")
def generations_dir_fixture(tmp_path: Path) -> Path:
    """世代の保存先."""
    return tmp_path / "generations"


@pytest.fixture(name="offline")
def offline_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """`app.db` を参照するとエラーになるようにする（CLI の forbid_database() と同じ状態）."""
    stub = local_run._OfflineDatabaseModule("app.db")
    monkeypatch.setitem(sys.modules, "app.db", stub)
    monkeypatch.setattr(app, "db", stub)


def _run(
    roster_path: Path,
    generations_dir: Path,
    minutes: int = 0,
    **kwargs,
) -> local_run.RunResult:
    options = RunOptions(**({"max_steps": _SHORT_STEPS} | kwargs))
    return run_generation(
        load_roster(str(roster_path)),
        roster_path,
        options,
        generations_dir=generations_dir,
        now=_BASE_TIME + timedelta(minutes=minutes),
    )


def _battle(generation_dir: Path, index: int) -> BattleRecord:
    return BattleRecord.model_validate_json(
        (generation_dir / f"battle_{index:03d}.json").read_text(encoding="utf-8")
    )


# --- 実行と再現性 ---


def test_run_saves_generation_files(
    roster_path: Path, generations_dir: Path, offline: None
) -> None:
    """DB を使わずに実行し、manifest・ロスターのコピー・戦闘ごとの結果を保存すること."""
    result = _run(roster_path, generations_dir, rounds=2, seed=611, label="before")

    assert result.path == generations_dir / "20261005-213000_before"
    assert sorted(p.name for p in result.path.iterdir()) == [
        "battle_001.json",
        "battle_002.json",
        MANIFEST_FILE,
        ROSTER_FILE,
    ]
    assert (result.path / ROSTER_FILE).read_bytes() == roster_path.read_bytes()

    manifest = read_manifest(result.path)
    assert manifest == result.manifest
    assert manifest.label == "before"
    assert manifest.roster_name == "run_test"
    assert manifest.seed == 611
    assert manifest.rounds == 2
    assert manifest.max_steps == _SHORT_STEPS
    assert manifest.git.commit
    assert len(manifest.fuzzy_rules_hash) == 64
    assert manifest.theater_id == "solomon"
    assert [b.seed for b in manifest.battles] == [611, 612]
    assert manifest.summary.battles == 2
    assert manifest.summary.wins + manifest.summary.losses == 2

    battle = _battle(result.path, 1)
    assert battle.theater_name == "ソロモン宙域"
    assert battle.environment_name == "宇宙"
    assert battle.viewer_preset == "SPACE"
    assert battle.player_info["name"] == "Zaku II"
    assert len(battle.enemies_info) == 3
    assert len(battle.map_bounds) == 2
    assert battle.steps_used <= _SHORT_STEPS
    # strip_debug_fields() を通さないため、デバッグ項目が残る。
    assert battle.logs
    assert all("fuzzy_scores" in log for log in battle.logs)


def test_same_seed_reproduces_same_logs(
    roster_path: Path, generations_dir: Path
) -> None:
    """同じロスター・同じシードなら、全戦闘のファイルが一致すること."""
    first = _run(roster_path, generations_dir, rounds=2, seed=611, label="a")
    second = _run(
        roster_path, generations_dir, minutes=1, rounds=2, seed=611, label="b"
    )

    for name in ("battle_001.json", "battle_002.json"):
        assert (first.path / name).read_bytes() == (second.path / name).read_bytes()


def test_each_battle_depends_only_on_its_seed(
    roster_path: Path, generations_dir: Path
) -> None:
    """N 戦目は、前の戦闘に関係なく seed + N - 1 だけで決まること."""
    two_rounds = _run(roster_path, generations_dir, rounds=2, seed=611, label="a")
    single = _run(roster_path, generations_dir, minutes=1, seed=612, label="b")

    assert _battle(two_rounds.path, 2).logs == _battle(single.path, 1).logs


def test_different_seed_changes_logs(roster_path: Path, generations_dir: Path) -> None:
    """シードを変えるとログが変わること."""
    a = _run(roster_path, generations_dir, seed=1, label="a")
    b = _run(roster_path, generations_dir, minutes=1, seed=2, label="b")

    assert _battle(a.path, 1).logs != _battle(b.path, 1).logs


def test_seed_is_chosen_and_recorded_when_omitted(
    roster_path: Path, generations_dir: Path
) -> None:
    """シードを省略すると、決めたシードを manifest に記録すること."""
    result = _run(roster_path, generations_dir, max_steps=1)

    assert result.manifest.seed >= 0
    assert result.manifest.battles[0].seed == result.manifest.seed
    # ラベルを省略するとロスター名になる。
    assert result.manifest.label == "run_test"


def test_run_restores_global_state(roster_path: Path, generations_dir: Path) -> None:
    """実行後は、エースのデータを DB から読み、numpy の乱数を固定しない状態に戻すこと."""
    _run(roster_path, generations_dir, seed=611, max_steps=1)

    assert gamedata._static_ace_pilots is None
    assert new_numpy_rng().random() != new_numpy_rng().random()


def test_offline_guard_rejects_database_access(offline: None) -> None:
    """ロスターのエースを渡さなければ、DB を読もうとしてエラーになること."""
    with pytest.raises(OfflineDatabaseError):
        get_ace_pilots()


def test_failed_run_leaves_no_generation(
    roster_path: Path, generations_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """途中で失敗した世代は残さないこと."""

    def fail(*_args, **_kwargs) -> BattleRecord:
        raise RuntimeError("boom")

    monkeypatch.setattr(local_run, "run_one_battle", fail)
    with pytest.raises(RuntimeError):
        _run(roster_path, generations_dir, seed=1)

    assert list(generations_dir.iterdir()) == []
    assert gamedata._static_ace_pilots is None


def test_invalid_roster_leaves_no_state(
    roster_path: Path, generations_dir: Path
) -> None:
    """手で壊したロスターでも、エースの参照を DB に戻し、世代を残さないこと."""
    data = json.loads(roster_path.read_text(encoding="utf-8"))
    data["conditions"]["battlefield"]["obstacles"] = "broken"
    roster_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValidationError):
        _run(roster_path, generations_dir, seed=1)

    assert gamedata._static_ace_pilots is None
    assert not generations_dir.exists() or list(generations_dir.iterdir()) == []


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"rounds": 0}, "--rounds"),
        ({"max_steps": 0}, "--steps"),
        ({"label": "../escape"}, "ラベル"),
    ],
)
def test_run_rejects_invalid_options(
    roster_path: Path, generations_dir: Path, options: dict, message: str
) -> None:
    """戦闘数・最大ステップ数・ラベルが不正なら ValueError にすること."""
    with pytest.raises(ValueError, match=message):
        _run(roster_path, generations_dir, **options)


def test_player_is_first_non_npc_entry(roster_path: Path) -> None:
    """プレイヤーの機体の先頭で判定し、全機が NPC なら先頭の機体にすること."""
    roster = load_roster(str(roster_path))
    npc_first = roster.model_copy(
        update={"entries": [roster.entries[1], roster.entries[0]]}
    )
    assert player_entry_index(npc_first) == 1

    all_npc = Roster.model_validate(
        roster.model_dump()
        | {"entries": [e.model_dump() | {"is_npc": True} for e in roster.entries]}
    )
    assert player_entry_index(all_npc) == 0


# --- 世代管理 ---


def test_sixth_run_removes_oldest_unpinned_generation(
    roster_path: Path, generations_dir: Path
) -> None:
    """6回目の実行で一番古い世代を消し、ピン留めした世代は残すこと."""
    pinned = _run(
        roster_path, generations_dir, label="pinned", pinned=True, max_steps=1
    )
    results = [
        _run(roster_path, generations_dir, minutes=i, label=f"g{i}", max_steps=1)
        for i in range(1, 6)
    ]
    assert all(r.removed == [] for r in results)

    sixth = _run(roster_path, generations_dir, minutes=6, label="g6", max_steps=1)

    assert sixth.removed == [results[0].path]
    remaining = [path.name for path, _ in list_generations(generations_dir)]
    assert remaining == [
        pinned.path.name,
        *(r.path.name for r in results[1:]),
        sixth.path.name,
    ]


def test_unpinned_generation_is_removed_on_next_run(
    roster_path: Path, generations_dir: Path
) -> None:
    """ピン留めを外した世代は、次の実行で5世代を超えれば消えること."""
    first = _run(roster_path, generations_dir, label="first", max_steps=1)
    set_pinned("first", True, generations_dir)
    for i in range(1, 6):
        _run(roster_path, generations_dir, minutes=i, label=f"g{i}", max_steps=1)
    assert first.path.exists()

    set_pinned("first", False, generations_dir)
    _run(roster_path, generations_dir, minutes=6, label="g6", max_steps=1)

    assert not first.path.exists()
    assert len(list_generations(generations_dir)) == 5


def test_same_second_runs_get_distinct_directories(
    roster_path: Path, generations_dir: Path
) -> None:
    """同じ秒・同じラベルで実行しても、別の世代として保存すること."""
    a = _run(roster_path, generations_dir, label="x", max_steps=1)
    b = _run(roster_path, generations_dir, label="x", max_steps=1)

    assert a.path.name == "20261005-213000_x"
    assert b.path.name == "20261005-213000_x-2"


def test_find_generation_by_id_prefix_or_label(
    roster_path: Path, generations_dir: Path
) -> None:
    """世代ID・前方一致・ラベルで選べ、複数該当すればエラーにすること."""
    a = _run(roster_path, generations_dir, label="before", max_steps=1)
    _run(roster_path, generations_dir, minutes=1, label="after", max_steps=1)

    assert find_generation(a.path.name, generations_dir)[0] == a.path
    assert find_generation("20261005-2130", generations_dir)[0] == a.path
    assert find_generation("before", generations_dir)[0] == a.path
    with pytest.raises(ValueError, match="複数"):
        find_generation("20261005-", generations_dir)
    with pytest.raises(ValueError, match="見つかりません"):
        find_generation("nothing", generations_dir)


def test_pin_and_unpin_update_manifest(
    roster_path: Path, generations_dir: Path
) -> None:
    """Pin / unpin で manifest のピン留め状態を書き換えること."""
    result = _run(roster_path, generations_dir, label="g", max_steps=1)

    set_pinned("g", True, generations_dir)
    assert read_manifest(result.path).pinned is True
    set_pinned("g", False, generations_dir)
    assert read_manifest(result.path).pinned is False
