/* frontend/src/hooks/useBattleLogic.ts */
import { useCallback, useMemo } from "react";
import { BattleLog, BattleResult, MobileSuit } from "@/types/battle";
import { isProductionDebugLog } from "@/utils/logFormatter";

/**
 * バトル詳細表示に必要な計算ロジックをカプセル化するカスタムフック。
 * - playerTeamIds: 自機・僚機の ID セット
 * - ownedMobileSuitIds: 所有機体 ID セット
 * - filterRelevantLogs: ログフィルタリング関数
 */
export function useBattleLogic(
  selectedBattle: BattleResult | null,
  mobileSuits: MobileSuit[] | undefined,
  isFiltered: boolean,
  isProduction: boolean = false
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

  /** ログフィルタリング:
   * - 本番環境（isProduction）ではデバッグログを除外し、自機フォーカスフィルタを適用
   * - 開発環境の手動フィルタ（isFiltered）: 自機/僚機のアクション or 自機がターゲット
   */
  const filterRelevantLogs = useCallback(
    (logs: BattleLog[]): BattleLog[] => {
      let result = logs;

      // 本番環境ではデバッグログを除外
      if (isProduction) {
        result = result.filter((log) => !isProductionDebugLog(log.message));
      }

      // 自機フォーカスフィルタ（isFiltered または isProduction 時に適用）
      if ((isFiltered || isProduction) && playerId) {
        result = result.filter(
          (log) =>
            playerTeamIds.has(log.actor_id) ||
            (log.target_id != null && log.target_id === playerId)
        );
      }

      return result;
    },
    [isFiltered, isProduction, playerId, playerTeamIds]
  );

  return { ownedMobileSuitIds, playerTeamIds, playerId, filterRelevantLogs };
}
