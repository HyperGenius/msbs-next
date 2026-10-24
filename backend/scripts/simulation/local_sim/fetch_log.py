"""本番の戦闘の解析用ログを取得し、ローカルシミュレータの世代として保存する.

バトル結果（またはルーム）から `battle_log_id` を引き、GCS の解析用ログ
（`fuzzy_scores` などのデバッグ項目つき）と `BattleResult` の表示用項目を `battle_001.json` にする。
DB は Read Only の接続で読むだけで、書き込まない。
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import Session, col, select

from app.models.models import BattleResult, Mission
from app.services.theater_service import TheaterService
from scripts.simulation.local_sim.analysis import GenerationAnalyzer, write_report
from scripts.simulation.local_sim.generations import (
    GENERATIONS_DIR,
    KEEP_UNPINNED_GENERATIONS,
    BattleRecord,
    GenerationSummary,
    GenerationWriter,
    GitInfo,
    Manifest,
    prune_generations,
    validate_label,
)

# 戦闘の記録は1世代に1戦。
_BATTLE_INDEX = 1


class BattleResultNotFoundError(ValueError):
    """指定したバトル結果・ルームが本番DBに無いことを表す."""


class AnalysisLogUnavailableError(ValueError):
    """解析用ログを取得できないことを表す."""


def find_battle_result(
    session: Session,
    result_id: uuid.UUID | None = None,
    room_id: uuid.UUID | None = None,
    user_id: str | None = None,
) -> tuple[BattleResult, int]:
    """バトル結果IDか、ルームIDからバトル結果を1件選ぶ.

    ルームは参加者ごとに結果を持つ。ルームIDで指定したときは、`user_id` に合う結果、
    無ければエントリーが早い結果を選ぶ。ログは全参加者で共有しているため、どれでも戦闘は同じ。

    Returns:
        選んだバトル結果と、同じルームの結果の件数

    Raises:
        BattleResultNotFoundError: 該当する結果が無い場合
        ValueError: 指定の組み合わせが不正な場合
    """
    if (result_id is None) == (room_id is None):
        raise ValueError("バトル結果ID か ルームID のどちらか1つを指定してください。")
    if result_id is not None:
        result = session.get(BattleResult, result_id)
        if result is None:
            raise BattleResultNotFoundError(
                f"バトル結果 {result_id} が見つかりません。"
            )
        return result, 1

    stmt = select(BattleResult).where(BattleResult.room_id == room_id)
    if user_id is not None:
        stmt = stmt.where(BattleResult.user_id == user_id)
    results = list(
        session.exec(
            stmt.order_by(col(BattleResult.created_at), col(BattleResult.id))
        ).all()
    )
    if not results:
        raise BattleResultNotFoundError(
            f"ルーム {room_id} のバトル結果が見つかりません。"
        )
    return results[0], len(results)


def count_steps(logs: list[dict[str, Any]]) -> int:
    """ログの時刻の種類数をステップ数の目安にする（本番はステップ数を保存していない）."""
    return len({log.get("timestamp") for log in logs})


def build_battle_record(
    result: BattleResult,
    logs: list[dict[str, Any]],
    theater_name: str | None,
    environment_name: str | None,
    viewer_preset: str | None,
    mission_name: str | None = None,
) -> BattleRecord:
    """バトル結果と解析用ログから `battle_001.json` の中身を作る.

    作戦ルームの結果は、作戦の結果（`objective_*`）も引き継ぐ。

    Raises:
        ValueError: 表示に必要な項目が結果に無い場合。勝敗が WIN / LOSE / DRAW 以外の場合
    """
    if result.win_loss not in ("WIN", "LOSE", "DRAW"):
        raise ValueError(f"勝敗 '{result.win_loss}' は取り込めません。")
    if (
        result.player_info is None
        or result.enemies_info is None
        or result.obstacles_info is None
        or result.map_bounds is None
    ):
        raise ValueError(
            "このバトル結果には、機体・障害物・フィールド範囲の表示用項目がありません。"
        )
    elapsed_time = max(
        (float(log.get("timestamp") or 0.0) for log in logs), default=0.0
    )
    return BattleRecord(
        index=_BATTLE_INDEX,
        win_loss=result.win_loss,  # type: ignore[arg-type]
        kills=result.kills,
        elapsed_time=elapsed_time,
        steps_used=count_steps(logs),
        # 本番は打ち切りを保存していない。
        timed_out=False,
        environment=result.environment,
        theater_id=result.theater_id,
        theater_name=theater_name,
        environment_name=environment_name,
        viewer_preset=viewer_preset,
        minovsky_density=result.minovsky_density or 0.0,
        player_info=result.player_info,
        enemies_info=result.enemies_info,
        obstacles_info=result.obstacles_info,
        map_bounds=result.map_bounds,
        part_hit_summary=result.part_hit_summary,
        weapon_accuracy_summary=result.weapon_accuracy_summary,
        detection_summary=result.detection_summary,
        mission_id=result.mission_id,
        mission_name=mission_name,
        objective_status=result.objective_status,  # type: ignore[arg-type]
        objective_progress=result.objective_progress,
        objective_required=result.objective_required,
        objective_detail=result.objective_detail,
        logs=logs,
    )


def save_production_generation(
    result: BattleResult,
    logs: list[dict[str, Any]],
    session: Session,
    label: str | None = None,
    pinned: bool = False,
    generations_dir: Path = GENERATIONS_DIR,
    keep: int = KEEP_UNPINNED_GENERATIONS,
    now: datetime | None = None,
) -> tuple[Path, Manifest, list[Path]]:
    """本番の1戦を、1戦だけの世代として保存し、世代管理で消した世代を返す.

    Raises:
        ValueError: ラベルが不正な場合。結果の項目が足りない場合
    """
    label = validate_label(label or f"prod-{str(result.id)[:8]}")
    created_at = now or datetime.now().astimezone()
    labels = TheaterService.labels_for(session, [result])[0]
    mission = (
        session.get(Mission, result.mission_id)
        if result.mission_id is not None
        else None
    )
    record = build_battle_record(
        result,
        logs,
        theater_name=labels.theater_name,
        environment_name=labels.environment_name,
        viewer_preset=labels.viewer_preset,
        mission_name=mission.name if mission else None,
    )

    writer = GenerationWriter(label, created_at, generations_dir)
    try:
        summary = writer.write_battle(record)
        analyzer = GenerationAnalyzer()
        analyzer.add(record)
        manifest = Manifest(
            generation_id=writer.generation_id,
            label=label,
            created_at=created_at,
            pinned=pinned,
            source="production",
            source_battle_result_id=str(result.id),
            source_room_id=str(result.room_id) if result.room_id else None,
            roster_name=None,
            roster_file=None,
            player_name=record.player_info.get("name"),
            rounds=1,
            # 取得時点のコードは、本番で戦闘したコードとは限らない。
            git=GitInfo(),
            theater_id=result.theater_id,
            environment=result.environment,
            minovsky_density=record.minovsky_density,
            mission_id=record.mission_id,
            mission_name=record.mission_name,
            summary=GenerationSummary.of([summary]),
            battles=[summary],
        )
        write_report(writer.tmp_dir, analyzer.result(writer.generation_id))
        path = writer.commit(manifest)
    except BaseException:
        writer.discard()
        raise
    return path, manifest, prune_generations(generations_dir, keep)
