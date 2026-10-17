"""旧形式と配信用ログの一致テストに使う戦闘のログを作る（replay-fixture）.

ロスターの機体で1戦を回し、同じ戦闘の旧形式（`strip_debug_fields()` の出力）と
配信用ログ（`to_replay_logs()` の出力）を、機体の情報と一緒に gzip した JSON に書く。
フロントの `tests/unit/replayLogParity.test.ts` と、バックエンドの
`tests/unit/test_replay_log.py` が同じファイルを読む。
このモジュールは `app` を import する。DB には接続しない。
"""

import gzip
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.engine.replay_log import to_replay_logs
from app.models.models import BattleLog
from scripts.simulation.local_sim.log_bench import stored_format
from scripts.simulation.local_sim.roster import REPO_ROOT, Roster
from scripts.simulation.local_sim.run import (
    player_entry_index,
    roster_battle_state,
    roster_to_conditions,
    run_one_battle,
)

REPLAY_FIXTURE_PATH = (
    REPO_ROOT / "backend" / "tests" / "fixtures" / "replay_log_parity.json.gz"
)
# 撃破・クリティカル・EN の記録・相手の切り替えを含む戦闘になるシード。
DEFAULT_FIXTURE_SEED = 639
# リポジトリに置くため、ファイルが数百KBに収まる長さで打ち切る。
DEFAULT_FIXTURE_STEPS = 600


class ReplayFixture(BaseModel):
    """同じ戦闘の旧形式と配信用ログ."""

    roster_name: str
    seed: int
    max_steps: int
    elapsed_time: float
    player_info: dict[str, Any]
    enemies_info: list[dict[str, Any]]
    stored_logs: list[dict[str, Any]]
    replay_logs: list[dict[str, Any]]


def build_replay_fixture(
    roster: Roster,
    seed: int = DEFAULT_FIXTURE_SEED,
    max_steps: int = DEFAULT_FIXTURE_STEPS,
) -> ReplayFixture:
    """ロスターで1戦を回し、旧形式と配信用ログを作る。プレイヤー機の選び方は `run` と同じ."""
    if max_steps < 1:
        raise ValueError("--steps は 1 以上で指定してください。")
    with roster_battle_state(roster):
        record = run_one_battle(
            roster,
            roster_to_conditions(roster.conditions),
            player_entry_index(roster),
            1,
            seed,
            max_steps,
        )
    logs = [BattleLog.model_validate(line) for line in record.logs]
    return ReplayFixture(
        roster_name=roster.name,
        seed=seed,
        max_steps=max_steps,
        elapsed_time=record.elapsed_time,
        player_info=record.player_info,
        enemies_info=record.enemies_info,
        stored_logs=stored_format(logs),
        replay_logs=to_replay_logs(logs),
    )


def write_replay_fixture(fixture: ReplayFixture, path: Path) -> int:
    """フィクスチャを gzip した JSON で書き、書いたバイト数を返す.

    gzip のヘッダーの時刻を 0 にする。同じ戦闘なら同じバイト列になる。
    """
    data = gzip.compress(
        fixture.model_dump_json().encode("utf-8"), compresslevel=9, mtime=0
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return len(data)


def read_replay_fixture(path: Path = REPLAY_FIXTURE_PATH) -> ReplayFixture:
    """`write_replay_fixture()` で書いたファイルを読む."""
    return ReplayFixture.model_validate_json(gzip.decompress(path.read_bytes()))
