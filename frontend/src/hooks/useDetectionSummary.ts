/* frontend/src/hooks/useDetectionSummary.ts */
import { useMemo } from "react";
import { BattleLog, BattleResult, DetectionSummary, MobileSuit } from "@/types/battle";

/**
 * ログから自機が索敵に成功した敵機数を集計する。
 * `backend/app/engine/result_summary.py` の `compute_detection_summary()` と同じ結果を返す。
 */
export function computeDetectionSummary(
  playerId: string | null,
  logs: BattleLog[],
  enemies: MobileSuit[]
): DetectionSummary {
  const total = enemies.length;
  if (!playerId) return { captured: 0, total };

  const capturedIds = new Set<string>();
  for (const log of logs) {
    if (log.action_type === "DETECTION" && log.actor_id === playerId && log.target_id) {
      capturedIds.add(log.target_id);
    }
  }

  return { captured: capturedIds.size, total };
}

/**
 * バトル結果の索敵状況（捕捉した敵機数/総数）を取得する（Issue #521）。
 * 保存済みの `battle.detection_summary` を優先する。
 * 無い場合（保存を始める前の結果）はログから計算する。
 */
export function useDetectionSummary(
  battle: BattleResult,
  logs: BattleLog[],
  playerId: string | null,
  enemies: MobileSuit[]
): DetectionSummary {
  const saved = battle.detection_summary;
  return useMemo(
    () => saved ?? computeDetectionSummary(playerId, logs, enemies),
    [saved, logs, playerId, enemies]
  );
}
