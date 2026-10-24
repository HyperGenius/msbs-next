"""ロスターから本番と同じ戦闘処理でバトルを実行し、1世代として保存する.

このモジュールは `app` を import する。DB には接続しない。
CLI は import する前に `forbid_database()` を呼び、DB を使う処理があればエラーにする。
"""

import copy
import secrets
import sys
import types
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.core.gamedata import use_static_ace_pilots
from app.engine.constants import FUZZY_RULES_DIR
from app.engine.environment import EnvironmentProfile
from app.engine.result_summary import compute_result_summary_fields
from app.engine.rng import seed_numpy_rngs
from app.models.models import BattleField, Mission
from app.services.battle_execution import (
    DEFAULT_MAX_STEPS,
    build_battlefield_view_fields,
    build_unit_view_fields,
    prepare_battle_units,
    run_battle,
    seed_battle_rngs,
    snapshot_to_mobile_suit,
)
from app.services.mission_battle import (
    WIN_LOSS_BY_OBJECTIVE_STATUS,
    build_mission_battle,
    objective_result_fields,
)
from app.services.theater_service import BattleConditions
from scripts.simulation.local_sim.analysis import GenerationAnalyzer, write_report
from scripts.simulation.local_sim.generations import (
    GENERATIONS_DIR,
    KEEP_UNPINNED_GENERATIONS,
    BattleRecord,
    BattleSummary,
    GenerationSummary,
    GenerationWriter,
    Manifest,
    directory_hash,
    git_info,
    prune_generations,
    validate_label,
)
from scripts.simulation.local_sim.roster import Roster, RosterConditions

# 2**31 未満にしておくと、シードを他のツールの引数にそのまま渡せる。
_MAX_RANDOM_SEED = 2**31
# 作戦の友軍・敵機の ID を作戦マスターでの位置から決める。
# 戦闘ごとに ID が変わると、report の機体ごとの集計が戦闘の数だけ分かれる。
_MISSION_UNIT_ID_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "msbs-local-sim/mission")


class OfflineDatabaseError(RuntimeError):
    """DB に接続しない実行で DB が使われたことを表す."""


class _OfflineDatabaseModule(types.ModuleType):
    def __getattr__(self, name: str) -> object:
        # import の仕組みが参照する `__path__` などは、無い属性として扱う。
        if name.startswith("__"):
            raise AttributeError(name)
        raise OfflineDatabaseError(
            f"run は DB に接続しません。app.db.{name} が参照されました。"
        )


def forbid_database() -> None:
    """`app.db` を、参照するとエラーになるモジュールに差し替える.

    `app.db` は import 時に `NEON_DATABASE_URL` でエンジンを作る。
    差し替えておけば、接続文字列が設定されていても接続しない。

    Raises:
        OfflineDatabaseError: `app.db` が既に import されている場合
    """
    if "app.db" in sys.modules:
        if isinstance(sys.modules["app.db"], _OfflineDatabaseModule):
            return
        raise OfflineDatabaseError("app.db が先に import されています。")
    sys.modules["app.db"] = _OfflineDatabaseModule("app.db")


@dataclass
class RunOptions:
    """`run` の実行条件."""

    rounds: int = 1
    max_steps: int = DEFAULT_MAX_STEPS
    # None なら実行時にランダムに決める。
    seed: int | None = None
    # None ならロスター名。
    label: str | None = None
    pinned: bool = False


@dataclass
class RunResult:
    """`run` で保存した世代と、世代管理で消した世代."""

    path: Path
    manifest: Manifest
    removed: list[Path]


def roster_to_conditions(conditions: RosterConditions) -> BattleConditions:
    """ロスターの戦域条件を `BattleSimulator` に渡す形に戻す."""
    profile = conditions.environment_profile
    return BattleConditions(
        theater_id=conditions.theater_id,
        environment=conditions.environment,
        environment_profile=(
            EnvironmentProfile(**profile.model_dump()) if profile else None
        ),
        minovsky_density=conditions.minovsky_density,
        battlefield=BattleField.model_validate(conditions.battlefield),
    )


def roster_mission(roster: Roster) -> Mission | None:
    """ロスターの作戦マスターを `Mission` に戻す。作戦が無ければ None."""
    if roster.mission is None:
        return None
    return Mission.model_validate(roster.mission.master)


def player_entry_index(roster: Roster) -> int:
    """勝敗と撃墜数を判定する機体を選ぶ.

    本番と同じく、プレイヤーの機体の先頭にする。全機が NPC なら先頭の機体にする。
    """
    for index, entry in enumerate(roster.entries):
        if not entry.is_npc:
            return index
    return 0


def run_one_battle(
    roster: Roster,
    conditions: BattleConditions,
    player_index: int,
    index: int,
    seed: int,
    max_steps: int,
    mission: Mission | None = None,
) -> BattleRecord:
    """ロスターの機体で1戦を実行する.

    作戦があれば、本番バッチの作戦ルームと同じ手順で友軍・敵機・配置・目標を組み立て、
    勝敗を作戦の結果で決める。
    `snapshot_to_mobile_suit()` が dict を書き換えるため、スナップショットはコピーして渡す。
    """
    snapshots = [entry.snapshot for entry in roster.entries]
    player_snapshot = snapshots[player_index]
    others = [s for i, s in enumerate(snapshots) if i != player_index]

    seed_battle_rngs(seed)
    player_unit, enemy_units = prepare_battle_units(
        copy.deepcopy(player_snapshot), copy.deepcopy(others)
    )
    mission_fields: dict = {}
    if mission is None:
        outcome = run_battle(player_unit, enemy_units, conditions, max_steps=max_steps)
        win_loss = "WIN" if outcome.player_win else "LOSE"
    else:
        # 作戦ルームと同じく、プレイヤーは全員同じチームで出る。
        other_players = enemy_units
        for unit in other_players:
            unit.side = "PLAYER"
        setup = build_mission_battle(
            mission,
            [player_unit, *other_players],
            conditions,
            unit_id_namespace=_MISSION_UNIT_ID_NAMESPACE,
        )
        conditions = setup.conditions
        enemy_units = [*other_players, *setup.mission_units]
        outcome = run_battle(
            player_unit,
            enemy_units,
            conditions,
            max_steps=max_steps,
            objective=setup.objective,
            retreat_points=setup.retreat_points,
            unit_assignments=setup.unit_assignments,
        )
        assert outcome.objective_result is not None
        win_loss = WIN_LOSS_BY_OBJECTIVE_STATUS[outcome.objective_result.status]
        mission_fields = {
            "mission_id": mission.id,
            "mission_name": mission.name,
            **objective_result_fields(outcome.objective_result, outcome.simulator),
        }
    simulator = outcome.simulator

    # 本番と同じく、player_info はエントリー時点、enemies_info は戦闘後の状態にする。
    entry_unit = snapshot_to_mobile_suit(copy.deepcopy(player_snapshot))
    unit_fields = build_unit_view_fields(entry_unit, [player_unit, *enemy_units])
    labels = roster.conditions
    return BattleRecord(
        index=index,
        seed=seed,
        win_loss=win_loss,
        kills=outcome.kills,
        elapsed_time=simulator.elapsed_time,
        steps_used=outcome.steps_used,
        timed_out=not simulator.is_finished,
        environment=conditions.environment,
        theater_id=conditions.theater_id,
        theater_name=labels.theater_name or conditions.theater_id,
        environment_name=labels.environment_name,
        viewer_preset=labels.viewer_preset,
        minovsky_density=conditions.minovsky_density,
        logs=[log.model_dump(mode="json") for log in simulator.logs],
        **unit_fields,
        **build_battlefield_view_fields(simulator),
        **compute_result_summary_fields(
            player_unit, simulator.logs, len(unit_fields["enemies_info"])
        ),
        **mission_fields,
    )


def _objective_progress_label(record: BattleRecord) -> str:
    """作戦の達成度の表示（例: ` / 離脱 2/3`）。友軍を数えない目標では空にする."""
    total = (record.objective_detail or {}).get("total")
    if not total:
        return ""
    return f" / 離脱 {record.objective_progress}/{total}"


@contextmanager
def roster_battle_state(roster: Roster) -> Iterator[None]:
    """ロスターのエースを渡す。抜けるときに、エースの参照と numpy の乱数を元に戻す.

    どちらもプロセス全体の状態のため、例外で抜けても必ず戻す。
    """
    use_static_ace_pilots(roster.ace_pilots)
    try:
        yield
    finally:
        use_static_ace_pilots(None)
        seed_numpy_rngs(None)


def run_generation(
    roster: Roster,
    roster_path: Path,
    options: RunOptions,
    generations_dir: Path = GENERATIONS_DIR,
    keep: int = KEEP_UNPINNED_GENERATIONS,
    now: datetime | None = None,
) -> RunResult:
    """ロスターで `options.rounds` 回戦闘し、1世代として保存する.

    保存後、ピン留めしていない世代が keep を超えた分を古い順に消す。

    Raises:
        ValueError: 戦闘数・最大ステップ数・ラベルが不正な場合
    """
    if options.rounds < 1:
        raise ValueError("--rounds は 1 以上で指定してください。")
    if options.max_steps < 1:
        raise ValueError("--steps は 1 以上で指定してください。")
    label = validate_label(options.label or roster.name)
    seed = (
        options.seed
        if options.seed is not None
        else secrets.randbelow(_MAX_RANDOM_SEED)
    )
    created_at = now or datetime.now().astimezone()

    conditions = roster_to_conditions(roster.conditions)
    mission = roster_mission(roster)
    player_index = player_entry_index(roster)
    writer = GenerationWriter(label, created_at, generations_dir)
    try:
        writer.write_roster(roster_path)
        battles: list[BattleSummary] = []
        analyzer = GenerationAnalyzer()
        with roster_battle_state(roster):
            for index in range(1, options.rounds + 1):
                record = run_one_battle(
                    roster,
                    conditions,
                    player_index,
                    index,
                    seed + index - 1,
                    options.max_steps,
                    mission,
                )
                summary = writer.write_battle(record)
                analyzer.add(record)
                battles.append(summary)
                print(
                    f"  [{index}/{options.rounds}] seed={summary.seed}"
                    f" {summary.win_loss} 撃墜 {summary.kills}"
                    f" / {summary.elapsed_time:.1f}s"
                    + _objective_progress_label(record)
                    + (" (打ち切り)" if summary.timed_out else "")
                )

        manifest = Manifest(
            generation_id=writer.generation_id,
            label=label,
            created_at=created_at,
            pinned=options.pinned,
            roster_name=roster.name,
            player_entry_index=player_index,
            player_name=roster.entries[player_index].snapshot.get("name"),
            seed=seed,
            rounds=options.rounds,
            max_steps=options.max_steps,
            git=git_info(),
            fuzzy_rules_hash=directory_hash(FUZZY_RULES_DIR),
            theater_id=conditions.theater_id,
            environment=conditions.environment,
            minovsky_density=conditions.minovsky_density,
            mission_id=mission.id if mission else None,
            mission_name=mission.name if mission else None,
            summary=GenerationSummary.of(battles),
            battles=battles,
        )
        write_report(writer.tmp_dir, analyzer.result(writer.generation_id))
        path = writer.commit(manifest)
    except BaseException:
        writer.discard()
        raise

    removed = prune_generations(generations_dir, keep)
    return RunResult(path=path, manifest=manifest, removed=removed)
