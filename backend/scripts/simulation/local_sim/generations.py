"""ローカルシミュレーションの実行結果（世代）の JSON スキーマと保存・世代管理.

1回の `run` を1世代として `generations/<日時>_<ラベル>/` に保存する。
このモジュールは `app` を import しない。
"""

import hashlib
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from scripts.simulation.local_sim.roster import (
    LOCAL_SIM_DIR,
    REPO_ROOT,
    ROSTER_NAME_PATTERN,
)

GENERATION_SCHEMA_VERSION = 1
GENERATIONS_DIR = LOCAL_SIM_DIR / "generations"
MANIFEST_FILE = "manifest.json"
ROSTER_FILE = "roster.json"
# ピン留めしていない世代をこの数だけ残す。
KEEP_UNPINNED_GENERATIONS = 5
GENERATION_TIME_FORMAT = "%Y%m%d-%H%M%S"
# 書き込み中の世代はこの接頭辞の一時ディレクトリに置く。一覧と世代管理の対象外。
_TMP_PREFIX = ".tmp-"

WinLoss = Literal["WIN", "LOSE"]


class GitInfo(BaseModel):
    """実行時のコードの状態。git が無ければ null."""

    commit: str | None = None
    dirty: bool | None = Field(
        default=None, description="未コミットの変更（未追跡のファイルを含む）があるか"
    )


class BattleSummary(BaseModel):
    """1戦の勝敗。`manifest.json` の一覧と `list` の集計に使う."""

    index: int = Field(description="1 始まりの戦闘番号")
    file: str
    seed: int
    win_loss: WinLoss
    kills: int
    elapsed_time: float = Field(description="戦闘の経過時間（秒）")
    steps_used: int
    timed_out: bool = Field(description="最大ステップ数で打ち切ったか")


class GenerationSummary(BaseModel):
    """世代全体の勝敗."""

    battles: int
    wins: int
    losses: int
    timeouts: int
    total_kills: int

    @classmethod
    def of(cls, battles: list[BattleSummary]) -> "GenerationSummary":
        """戦闘ごとの勝敗を集計する."""
        wins = sum(1 for b in battles if b.win_loss == "WIN")
        return cls(
            battles=len(battles),
            wins=wins,
            losses=len(battles) - wins,
            timeouts=sum(1 for b in battles if b.timed_out),
            total_kills=sum(b.kills for b in battles),
        )


class Manifest(BaseModel):
    """世代の実行条件・再現情報・勝敗サマリー・ピン留め状態（`manifest.json`）."""

    schema_version: int = GENERATION_SCHEMA_VERSION
    generation_id: str = Field(description="世代ディレクトリの名前")
    label: str
    created_at: datetime
    pinned: bool = False
    roster_name: str
    roster_file: str = ROSTER_FILE
    player_entry_index: int = Field(
        description="勝敗と撃墜数を判定する機体の、ロスターの entries での位置"
    )
    player_name: str | None = None
    seed: int = Field(description="1戦目のシード。N 戦目は seed + N - 1")
    rounds: int
    max_steps: int
    git: GitInfo
    fuzzy_rules_hash: str = Field(
        description="backend/data/fuzzy_rules/ の全ファイルの SHA-256"
    )
    theater_id: str | None = None
    environment: str
    minovsky_density: float
    summary: GenerationSummary
    battles: list[BattleSummary]


class BattleRecord(BaseModel):
    """1戦分の結果とログ（`battle_NNN.json`）.

    表示用の項目は本番の `BattleResult` と同じ名前にする。
    """

    schema_version: int = GENERATION_SCHEMA_VERSION
    index: int
    seed: int
    win_loss: WinLoss
    kills: int = Field(description="判定する機体自身の撃墜数")
    elapsed_time: float
    steps_used: int
    timed_out: bool
    environment: str
    theater_id: str | None = None
    theater_name: str | None = None
    environment_name: str | None = None
    viewer_preset: str | None = None
    minovsky_density: float
    player_info: dict[str, Any] = Field(description="エントリー時点の判定する機体")
    enemies_info: list[dict[str, Any]] = Field(
        description="判定する機体以外の全ユニット（戦闘後の状態）"
    )
    obstacles_info: list[dict[str, Any]]
    map_bounds: list[float]
    logs: list[dict[str, Any]] = Field(
        description="BattleLog の一覧。fuzzy_scores などのデバッグ項目を残す"
    )

    def summary(self, file: str) -> BattleSummary:
        """`manifest.json` に載せる勝敗を返す."""
        return BattleSummary(
            index=self.index,
            file=file,
            seed=self.seed,
            win_loss=self.win_loss,
            kills=self.kills,
            elapsed_time=self.elapsed_time,
            steps_used=self.steps_used,
            timed_out=self.timed_out,
        )


def battle_file_name(index: int) -> str:
    """戦闘番号からファイル名を返す（例: battle_001.json）."""
    return f"battle_{index:03d}.json"


def validate_label(label: str) -> str:
    """ラベルがディレクトリ名に使える文字だけか確かめる.

    Raises:
        ValueError: 英数字で始まらない、または英数字と `_.-` 以外を含む場合
    """
    if not ROSTER_NAME_PATTERN.fullmatch(label):
        raise ValueError(
            f"ラベル '{label}' は使えません。英数字で始め、英数字と _ . - だけを使ってください。"
        )
    return label


def git_info(repo_root: Path = REPO_ROOT) -> GitInfo:
    """HEAD のコミットと未コミットの変更の有無を返す."""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return GitInfo()
    return GitInfo(commit=commit, dirty=bool(status.strip()))


def directory_hash(directory: Path) -> str:
    """ディレクトリ配下の全ファイルの相対パスと中身から SHA-256 を作る."""
    digest = hashlib.sha256()
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        digest.update(path.relative_to(directory).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _write_json(path: Path, model: BaseModel, indent: int | None) -> None:
    path.write_text(
        model.model_dump_json(indent=indent) + "\n", encoding="utf-8", newline="\n"
    )


class GenerationWriter:
    """世代を一時ディレクトリに書き、全部書けたら世代ディレクトリへ移す.

    途中で失敗した世代は一時ディレクトリごと消え、一覧と世代管理に残らない。
    """

    def __init__(
        self,
        label: str,
        created_at: datetime,
        generations_dir: Path = GENERATIONS_DIR,
    ) -> None:
        """世代の名前を決めて一時ディレクトリを作る."""
        self.generations_dir = generations_dir
        self.generation_id = _unique_generation_id(
            generations_dir, f"{created_at.strftime(GENERATION_TIME_FORMAT)}_{label}"
        )
        self.tmp_dir = generations_dir / f"{_TMP_PREFIX}{self.generation_id}"
        self.tmp_dir.mkdir(parents=True)

    def write_roster(self, roster_path: Path) -> None:
        """実行時のロスターを、手で編集した内容も含めてそのままコピーする."""
        shutil.copyfile(roster_path, self.tmp_dir / ROSTER_FILE)

    def write_battle(self, record: BattleRecord) -> BattleSummary:
        """1戦分を保存する。1戦で数百 KB になるため、インデントを付けない."""
        file = battle_file_name(record.index)
        _write_json(self.tmp_dir / file, record, indent=None)
        return record.summary(file)

    def commit(self, manifest: Manifest) -> Path:
        """`manifest.json` を書き、世代ディレクトリへ移す."""
        _write_json(self.tmp_dir / MANIFEST_FILE, manifest, indent=2)
        path = self.generations_dir / self.generation_id
        self.tmp_dir.rename(path)
        return path

    def discard(self) -> None:
        """書きかけの世代を消す."""
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


def _unique_generation_id(generations_dir: Path, base: str) -> str:
    candidate = base
    suffix = 2
    while (generations_dir / candidate).exists() or (
        generations_dir / f"{_TMP_PREFIX}{candidate}"
    ).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def read_manifest(generation_dir: Path) -> Manifest:
    """世代の `manifest.json` を読む."""
    return Manifest.model_validate_json(
        (generation_dir / MANIFEST_FILE).read_text(encoding="utf-8")
    )


def list_generations(
    generations_dir: Path = GENERATIONS_DIR,
) -> list[tuple[Path, Manifest]]:
    """保存済みの世代を古い順に返す。`manifest.json` が無いディレクトリは除く."""
    if not generations_dir.is_dir():
        return []
    generations = [
        (path, read_manifest(path))
        for path in generations_dir.iterdir()
        if path.is_dir()
        and not path.name.startswith(_TMP_PREFIX)
        and (path / MANIFEST_FILE).is_file()
    ]
    return sorted(generations, key=lambda g: (g[1].created_at, g[0].name))


def prune_generations(
    generations_dir: Path = GENERATIONS_DIR,
    keep: int = KEEP_UNPINNED_GENERATIONS,
) -> list[Path]:
    """ピン留めしていない世代が keep を超えた分を古い順に消す.

    Returns:
        消した世代のディレクトリ
    """
    unpinned = [path for path, m in list_generations(generations_dir) if not m.pinned]
    removed = unpinned[: max(len(unpinned) - keep, 0)]
    for path in removed:
        shutil.rmtree(path)
    return removed


def find_generation(
    ref: str, generations_dir: Path = GENERATIONS_DIR
) -> tuple[Path, Manifest]:
    """世代ID、その前方一致、またはラベルで世代を1つ選ぶ.

    Raises:
        ValueError: 該当する世代が無い場合。複数ある場合
    """
    generations = list_generations(generations_dir)
    for path, manifest in generations:
        if path.name == ref:
            return path, manifest
    matches = [
        (path, manifest)
        for path, manifest in generations
        if path.name.startswith(ref) or manifest.label == ref
    ]
    if not matches:
        raise ValueError(f"世代 '{ref}' が見つかりません。")
    if len(matches) > 1:
        names = ", ".join(path.name for path, _ in matches)
        raise ValueError(f"世代 '{ref}' に該当する世代が複数あります: {names}")
    return matches[0]


def set_pinned(
    ref: str, pinned: bool, generations_dir: Path = GENERATIONS_DIR
) -> tuple[Path, Manifest]:
    """世代のピン留めを切り替える.

    ピン留めを外した世代は、次の `run` の世代管理で消える対象になる。
    """
    path, manifest = find_generation(ref, generations_dir)
    if manifest.pinned != pinned:
        manifest = manifest.model_copy(update={"pinned": pinned})
        _write_json(path / MANIFEST_FILE, manifest, indent=2)
    return path, manifest
