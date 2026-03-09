/* frontend/src/hooks/useBattleLogic.ts */
import { useCallback, useMemo } from "react";
import { BattleLog, BattleResult, MobileSuit } from "@/types/battle";

/**
 * バトル詳細表示に必要な計算ロジックをカプセル化するカスタムフック。
 * - playerTeamIds: 自機・僚機の ID セット
 * - ownedMobileSuitIds: 所有機体 ID セット
 * - filterRelevantLogs: ログフィルタリング関数
 */
export function useBattleLogic(
  selectedBattle: BattleResult | null,
  mobileSuits: MobileSuit[] | undefined,
  isFiltered: boolean
) {
  const ownedMobileSuitIds = useMemo(
    () => new Set(mobileSuits?.map((ms) => ms.id) ?? []),
    [mobileSuits]
  );

  /** player_info から自機・僚機の ID セットを算出
   * Note: enemies_info にはバッチ処理時の全非主要ユニットが含まれ、
   * 同じ team_id を持つユニットは僚機として扱う */
  const playerTeamIds = useMemo(() => {
    if (!selectedBattle?.player_info) return new Set<string>();
    const playerInfo = selectedBattle.player_info;
    const teamId = playerInfo.team_id ?? playerInfo.id;
    const ids = new Set<string>([playerInfo.id]);
    if (selectedBattle.enemies_info) {
      for (const e of selectedBattle.enemies_info) {
        if ((e.team_id ?? e.id) === teamId) {
          ids.add(e.id);
        }
      }
    }
    return ids;
  }, [selectedBattle]);

  const playerId = selectedBattle?.player_info?.id ?? null;

  /** ログフィルタリング: 自機/僚機のアクション or 自機がターゲット */
  const filterRelevantLogs = useCallback(
    (logs: BattleLog[]): BattleLog[] => {
      if (!isFiltered || !playerId) return logs;
      return logs.filter(
        (log) =>
          playerTeamIds.has(log.actor_id) ||
          (log.target_id != null && log.target_id === playerId)
      );
    },
    [isFiltered, playerId, playerTeamIds]
  );

  return { ownedMobileSuitIds, playerTeamIds, playerId, filterRelevantLogs };
}
