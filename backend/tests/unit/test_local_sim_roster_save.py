"""ローカルシミュレータの roster-save（標準入力のロスターの検証と保存）のテスト."""

import io
import json
from pathlib import Path

import pytest

from scripts.simulation.local_sim import __main__ as cli
from scripts.simulation.local_sim.roster import load_roster, save_roster

ROSTER = {
    "name": "original",
    "fetched_at": "2026-10-24T00:00:00",
    "conditions": {"environment": "SPACE"},
    "entries": [
        {
            "source": {"kind": "npc", "mobile_suit_id": "ms-1"},
            "is_npc": True,
            "snapshot": {"name": "ザク", "max_hp": 100},
        }
    ],
}


@pytest.fixture(name="rosters_dir")
def rosters_dir_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """保存先を一時ディレクトリに差し替える."""
    rosters_dir = tmp_path / "rosters"
    monkeypatch.setattr(
        cli,
        "save_roster",
        lambda roster, overwrite=False: save_roster(roster, rosters_dir, overwrite),
    )
    return rosters_dir


def _run(monkeypatch: pytest.MonkeyPatch, roster: dict, *args: str) -> int:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(roster)))
    return cli.main(["roster-save", *args])


def test_roster_save_renames_and_saves(
    rosters_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """標準入力のロスターを --name の名前で保存すること."""
    assert _run(monkeypatch, ROSTER, "--name", "edited") == 0

    saved = load_roster("edited", rosters_dir)
    assert saved.name == "edited"
    assert saved.entries[0].snapshot["max_hp"] == 100


def test_roster_save_does_not_overwrite_without_force(
    rosters_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """同名のロスターは --force が無ければ上書きしないこと."""
    assert _run(monkeypatch, ROSTER, "--name", "edited") == 0

    changed = {**ROSTER, "conditions": {"environment": "GROUND"}}
    assert _run(monkeypatch, changed, "--name", "edited") == 1
    assert "--force" in capsys.readouterr().err
    assert load_roster("edited", rosters_dir).conditions.environment == "SPACE"

    assert _run(monkeypatch, changed, "--name", "edited", "--force") == 0
    assert load_roster("edited", rosters_dir).conditions.environment == "GROUND"


def test_roster_save_rejects_invalid_roster(
    rosters_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Roster の形式に合わない入力は保存しないこと."""
    broken = {**ROSTER, "entries": [{"is_npc": True}]}

    assert _run(monkeypatch, broken, "--name", "broken") == 1
    assert not rosters_dir.exists()


def test_roster_save_rejects_invalid_name(
    rosters_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ファイル名に使えないロスター名は保存しないこと."""
    assert _run(monkeypatch, ROSTER, "--name", "../evil") == 1
    assert not rosters_dir.exists()
