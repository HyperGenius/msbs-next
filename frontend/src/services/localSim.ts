import useSWR from "swr";
import {
  BattleResult,
  LocalSimBattle,
  LocalSimGenerationList,
  LocalSimManifest,
} from "@/types/battle";
import { fetcher } from "./auth";
import { useNdjsonBattleLogs } from "./battle";

// 開発用バトルビューア（/dev/sim）の API。Next.js の Route Handler なので同じオリジンに送る。
const LOCAL_SIM_API = "/api/dev/sim/generations";

/** 戦闘の API の URL を返す。 */
export function localSimBattleUrl(generationId: string, index: number): string {
  return `${LOCAL_SIM_API}/${encodeURIComponent(generationId)}/battles/${index}`;
}

/** 保存済みの世代を新しい順に取得するSWRフック（開発環境専用） */
export function useLocalSimGenerations() {
  const { data, error, isLoading } = useSWR<LocalSimGenerationList>(LOCAL_SIM_API, fetcher, {
    revalidateOnFocus: false,
  });

  return {
    root: data?.root,
    generations: data?.generations,
    isLoading,
    isError: error,
  };
}

/** 1戦分のログ以外の項目を取得するSWRフック。generationId か index が null ならフェッチしない */
export function useLocalSimBattle(generationId: string | null, index: number | null) {
  const { data, error, isLoading } = useSWR<LocalSimBattle>(
    generationId && index !== null ? localSimBattleUrl(generationId, index) : null,
    fetcher,
    { revalidateOnFocus: false, revalidateOnReconnect: false }
  );

  return {
    battle: data,
    isLoading,
    isError: error,
  };
}

/** 1戦分のログを段階的に取得するSWRフック。返す値は `useBattleLogs` と同じ */
export function useLocalSimBattleLogs(generationId: string | null, index: number | null) {
  return useNdjsonBattleLogs(
    generationId && index !== null ? `${localSimBattleUrl(generationId, index)}/logs` : null
  );
}

/**
 * ローカルシミュレーションの1戦を、履歴詳細の部品に渡せる BattleResult にする。
 * 報酬・ダイジェストなど本番のバッチでだけ作る項目は持たない。
 */
export function localSimBattleToResult(
  manifest: LocalSimManifest,
  battle: LocalSimBattle
): BattleResult {
  return {
    id: `${manifest.generation_id}/${battle.index}`,
    user_id: null,
    mission_id: null,
    win_loss: battle.win_loss,
    environment: battle.environment,
    player_info: battle.player_info,
    enemies_info: battle.enemies_info,
    obstacles_info: battle.obstacles_info,
    map_bounds: battle.map_bounds,
    theater_id: battle.theater_id,
    minovsky_density: battle.minovsky_density,
    theater_name: battle.theater_name,
    environment_name: battle.environment_name,
    viewer_preset: battle.viewer_preset,
    kills: battle.kills,
    created_at: manifest.created_at,
  };
}
