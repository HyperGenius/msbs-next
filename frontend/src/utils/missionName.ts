/* frontend/src/utils/missionName.ts */
import { AvailableMission, BattleResult, Mission, ObjectiveSummary } from "@/types/battle";

/**
 * バトル結果の表示用のミッション名を返す.
 * ミッションIDが無いバトルは定期バトルとして、開催日付きの名前にする。
 */
export function getMissionName(
  missions: Mission[] | undefined,
  missionId: number | null,
  createdAt?: string,
): string {
  if (missionId && missions) {
    const mission = missions.find((m) => m.id === missionId);
    return mission?.name || `Mission ${missionId}`;
  }
  if (!missionId) {
    if (createdAt) {
      const d = new Date(createdAt);
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, "0");
      const dd = String(d.getDate()).padStart(2, "0");
      return `${yyyy}${mm}${dd} デイリーバトルロイヤル`;
    }
    return "デイリーバトルロイヤル";
  }
  return "Unknown Mission";
}

/** 作戦の目的を1文で返す（作戦の選択カード用） */
export function describeObjective(mission: AvailableMission): string {
  if (mission.objective_type === "RETREAT_SUPPORT") {
    const required = Number(mission.objective_params.required ?? 0);
    return `友軍を${mission.ally_count}機中${required}機以上、撤退ポイントまで逃がす`;
  }
  return "敵を殲滅する";
}

/** 作戦の結果の達成度を返す（例: 離脱 2/3）。数えない目標は null */
export function formatObjectiveProgress(
  progress: number | null | undefined,
  total: number | undefined,
): string | null {
  if (progress == null || !total) return null;
  return `離脱 ${progress}/${total}`;
}

/**
 * 作戦ルームの結果から、結果表示用の作戦の結果を取り出す.
 * バトルロイヤル（作戦IDなし）と、作戦の結果が無い既存の戦歴は null で、今までどおりの表示にする。
 */
export function getObjectiveSummary(
  battle: Pick<
    BattleResult,
    | "mission_id"
    | "objective_status"
    | "objective_progress"
    | "objective_required"
    | "objective_detail"
  >,
): ObjectiveSummary | null {
  if (battle.mission_id == null || !battle.objective_status) return null;
  return {
    status: battle.objective_status,
    progress: battle.objective_progress ?? null,
    required: battle.objective_required ?? null,
    total: battle.objective_detail?.total ?? null,
    lost: battle.objective_detail?.lost ?? null,
  };
}

/** 作戦の結果の見出し（成功・失敗・引き分け） */
export const OBJECTIVE_STATUS_LABELS: Record<ObjectiveSummary["status"], string> = {
  SUCCESS: "作戦成功",
  FAILURE: "作戦失敗",
  DRAW: "作戦 引き分け",
};
