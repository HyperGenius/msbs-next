/* frontend/src/hooks/useWeaponAccuracySummary.ts */
import { useMemo } from "react";
import { BattleLog } from "@/types/battle";

const ATTEMPT_ACTION_TYPES = new Set(["ATTACK", "MELEE_COMBO", "MISS"]);
const HIT_ACTION_TYPES = new Set(["ATTACK", "MELEE_COMBO"]);

/** 武装ごとの命中率1件分 */
export interface WeaponAccuracyStat {
  weaponName: string;
  hits: number;
  attempts: number;
  /** 試行0件の場合は null（「--%」表示用） */
  accuracy: number | null;
}

/**
 * ログから自機視点の武装ごとの命中率をクライアント側で計算する（Issue #521）。
 * サマリーパネルは事後分析用途のため、フィードバック目的を損なわないよう実数値のまま表示する
 * （ダメージ演出の抽象化とは異なる方針。issue #521 コメント参照）。
 *
 * @param equippedWeaponNames 自機の装備武器名一覧。一度も使用しなかった武器も
 *   0/0（「--%」表示）として一覧に含めるために渡す（省略時はログに登場した武器のみ集計する）。
 */
export function computeWeaponAccuracySummary(
  playerId: string | null,
  logs: BattleLog[],
  equippedWeaponNames: string[] = []
): WeaponAccuracyStat[] {
  if (!playerId) return [];

  const attempts: Record<string, number> = {};
  const hits: Record<string, number> = {};

  for (const name of equippedWeaponNames) {
    attempts[name] = attempts[name] ?? 0;
    hits[name] = hits[name] ?? 0;
  }

  for (const log of logs) {
    if (log.actor_id !== playerId) continue;
    if (!ATTEMPT_ACTION_TYPES.has(log.action_type)) continue;
    const weaponName = log.weapon_name ?? "格闘";

    attempts[weaponName] = (attempts[weaponName] ?? 0) + 1;
    if (HIT_ACTION_TYPES.has(log.action_type)) {
      hits[weaponName] = (hits[weaponName] ?? 0) + 1;
    }
  }

  return Object.keys(attempts)
    .map((weaponName) => {
      const attemptCount = attempts[weaponName];
      const hitCount = hits[weaponName] ?? 0;
      return {
        weaponName,
        hits: hitCount,
        attempts: attemptCount,
        accuracy: attemptCount > 0 ? hitCount / attemptCount : null,
      };
    })
    .sort((a, b) => b.attempts - a.attempts);
}

/** バトル結果の武装ごとの命中率を取得する（Issue #521） */
export function useWeaponAccuracySummary(
  logs: BattleLog[],
  playerId: string | null,
  equippedWeaponNames: string[] = []
): WeaponAccuracyStat[] {
  return useMemo(
    () => computeWeaponAccuracySummary(playerId, logs, equippedWeaponNames),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [logs, playerId, equippedWeaponNames.join(",")]
  );
}
