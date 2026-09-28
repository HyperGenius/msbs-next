/* frontend/src/utils/theater.ts */
import { BattleResult } from "@/types/battle";

type TheaterFields = Pick<
  BattleResult,
  "theater_name" | "environment_name" | "minovsky_density"
>;

/**
 * 戦域の表示名を返す（例: 「ソロモン宙域（宇宙）／ミノフスキー濃度 42%」）。
 * 戦域の無いバトルは null を返す。
 */
export function formatTheaterLabel(battle: TheaterFields): string | null {
  if (!battle.theater_name) return null;
  const environment = battle.environment_name
    ? `（${battle.environment_name}）`
    : "";
  const minovsky =
    battle.minovsky_density != null
      ? `／ミノフスキー濃度 ${Math.round(battle.minovsky_density * 100)}%`
      : "";
  return `${battle.theater_name}${environment}${minovsky}`;
}

/** BattleViewer に渡す環境を返す。描画プリセットが無いバトルは環境タイプIDを使う。 */
export function getViewerEnvironment(
  battle: Pick<BattleResult, "viewer_preset" | "environment">,
): string {
  return battle.viewer_preset ?? battle.environment ?? "SPACE";
}
