import { Vector3 } from "./geometry";
import { TheaterForecast } from "./theater";

/** 作戦の結果 */
export type ObjectiveStatus = "SUCCESS" | "FAILURE" | "DRAW";

/** 次回の開催でエントリーできる作戦（GET /api/missions/available） */
export interface AvailableMission {
  id: number;
  name: string;
  description: string;
  difficulty: number;
  /** 作戦目標の種類（ANNIHILATION / RETREAT_SUPPORT） */
  objective_type: string;
  /** 作戦目標の引数（撤退支援なら required） */
  objective_params: Record<string, unknown>;
  /** 戦う環境。戦域があれば戦域の環境タイプ */
  environment: string;
  ally_count: number;
  enemy_count: number;
}

/** GET /api/missions/available のレスポンス */
export interface AvailableMissionsResponse {
  /** 今回の開催の戦域。戦域の無い開催は null */
  theater: TheaterForecast | null;
  missions: AvailableMission[];
}

/** 撤退ポイント（BattleViewer の地面マーカー用） */
export interface RetreatPointView {
  position: Vector3;
  /** 有効半径 (m) */
  radius: number;
  /** 専用のチーム。null は全チーム共通 */
  team_id: string | null;
}

/** BattleResult.objective_detail。達成度の内訳と、ビューア用の撤退ポイント・ロール */
export interface ObjectiveDetail {
  /** 護衛対象の友軍の数 */
  total?: number;
  /** 撃破された友軍の数 */
  lost?: number;
  player_survived?: boolean;
  retreat_points?: RetreatPointView[];
  /** ユニットID → ロール（WITHDRAW など） */
  unit_roles?: Record<string, string>;
}

/** 結果表示用にまとめた作戦の結果 */
export interface ObjectiveSummary {
  status: ObjectiveStatus;
  /** 達成した数（離脱させた友軍の数など） */
  progress: number | null;
  /** 成功に必要な数。0・null は達成度を数えない */
  required: number | null;
  /** 護衛対象の数 */
  total: number | null;
  /** 撃破された友軍の数 */
  lost: number | null;
}
