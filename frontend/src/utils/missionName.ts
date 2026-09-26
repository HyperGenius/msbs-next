/* frontend/src/utils/missionName.ts */
import { Mission } from "@/types/battle";

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
