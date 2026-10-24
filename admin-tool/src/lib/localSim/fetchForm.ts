/* admin-tool/src/lib/localSim/fetchForm.ts */
// ロスター作成フォームの参加機体の行を、fetch の --ms / --pilot にする。
import type { LocalSimUnitSpec } from "@/types/localSim";

/**
 * 参加機体の行の種類。
 * - player: プレイヤーを選び、所有機から出撃機体を選ぶ（`--ms`。active_mobile_suit_id に依存しない）
 * - npc: NPC のパイロットを選ぶ（`--pilot`。出撃機体が未設定なら CLI が所有機の先頭にする）
 * - ms: 機体ID を直接入れる（`--ms`）
 */
export type FetchUnitKind = "player" | "npc" | "ms";

export interface FetchUnitRow {
  key: number;
  kind: FetchUnitKind;
  /** player / npc で選んだパイロット（pilots.id） */
  pilotId: string;
  /** player で選んだ所有機、または ms で入れた機体ID */
  mobileSuitId: string;
  team: string;
}

/** 行を `--ms` / `--pilot` の指定にする。選び終えていない行があれば理由の文字列を返す。 */
export function rowsToUnitSpecs(
  rows: FetchUnitRow[]
): { mobile_suits: LocalSimUnitSpec[]; pilots: LocalSimUnitSpec[] } | string {
  const mobileSuits: LocalSimUnitSpec[] = [];
  const pilots: LocalSimUnitSpec[] = [];
  for (const [index, row] of rows.entries()) {
    const team = row.team.trim() || null;
    const label = `参加機体 ${index + 1} 行目`;
    if (row.kind === "npc") {
      if (!row.pilotId) return `${label}: NPC のパイロットを選んでください。`;
      pilots.push({ id: row.pilotId, team });
      continue;
    }
    const id = row.mobileSuitId.trim();
    if (!id) {
      return row.kind === "player"
        ? `${label}: プレイヤーと出撃機体を選んでください。`
        : `${label}: 機体ID を入れてください。`;
    }
    mobileSuits.push({ id, team });
  }
  return { mobile_suits: mobileSuits, pilots };
}
