/* frontend/src/hooks/usePartHitSummary.ts */
import { useMemo } from "react";
import { BattleLog, BattleResult, PartHitStat, PartHitSummary } from "@/types/battle";

const HIT_ACTION_TYPES = new Set(["ATTACK", "MELEE_COMBO"]);

/**
 * ログからプレイヤー視点の部位別集計をクライアント側で計算する（バックエンドが
 * `part_hit_summary` を計算する前に保存された既存バトルレコード向けのフォールバック）。
 * 集計方法は `backend/app/engine/part_hit_summary.py` の
 * `compute_part_hit_summary()` と同一のロジックに揃えている。
 */
function computeFromLogs(playerId: string | null, logs: BattleLog[]): PartHitSummary {
  const taken: Record<string, PartHitStat> = {};
  const dealt: Record<string, PartHitStat> = {};
  if (!playerId) return { taken, dealt };

  for (const log of logs) {
    if (!HIT_ACTION_TYPES.has(log.action_type)) continue;

    if (log.target_id === playerId && log.hit_part) {
      const entry = taken[log.hit_part] ?? { hits: 0, damage: 0 };
      entry.hits += 1;
      entry.damage += log.damage ?? 0;
      taken[log.hit_part] = entry;
    }

    if (log.actor_id === playerId && log.weapon_slot_role) {
      const entry = dealt[log.weapon_slot_role] ?? { hits: 0, damage: 0 };
      entry.hits += 1;
      entry.damage += log.damage ?? 0;
      dealt[log.weapon_slot_role] = entry;
    }
  }

  return { taken, dealt };
}

/**
 * バトル結果の部位別命中サマリーを取得する（Issue #504）。
 * バックエンドが書き込み時に計算済みの `battle.part_hit_summary` があれば
 * それを優先し、無い場合（マイグレーション前の既存レコード）はロード済みの
 * ログからクライアント側で計算してフォールバック表示する。
 */
export function usePartHitSummary(
  battle: BattleResult,
  logs: BattleLog[],
  playerId: string | null
): PartHitSummary {
  return useMemo(() => {
    if (battle.part_hit_summary) return battle.part_hit_summary;
    return computeFromLogs(playerId, logs);
  }, [battle.part_hit_summary, logs, playerId]);
}
