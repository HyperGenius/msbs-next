/* frontend/src/hooks/useDetectionSummary.ts */
import { useMemo } from "react";
import { BattleLog, MobileSuit } from "@/types/battle";

/** 索敵状況サマリー（Issue #521） */
export interface DetectionSummary {
  /** 自機が索敵に成功した敵機数（重複なし） */
  captured: number;
  /** バトルに参加した敵機の総数 */
  total: number;
}

/** ログから自機が索敵に成功した敵機数を集計する */
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

/** バトル結果の索敵状況（捕捉した敵機数/総数）を取得する（Issue #521） */
export function useDetectionSummary(
  logs: BattleLog[],
  playerId: string | null,
  enemies: MobileSuit[]
): DetectionSummary {
  return useMemo(() => computeDetectionSummary(playerId, logs, enemies), [logs, playerId, enemies]);
}
