import { z } from "zod";
import {
  BlueprintTargetSummary,
  DropTableDetail,
  DropTableEntryDetail,
  DropTableUpdate,
  MasterMobileSuit,
  MasterWeapon,
} from "@/types/admin";

export const DROP_FACTIONS = ["FEDERATION", "ZEON"] as const;
export type DropFaction = (typeof DROP_FACTIONS)[number];

export const DROP_FACTION_LABELS: Record<DropFaction, string> = {
  FEDERATION: "連邦",
  ZEON: "ジオン",
};

export const TARGET_TYPE_LABELS: Record<BlueprintTargetSummary["target_type"], string> = {
  MOBILE_SUIT: "機体",
  WEAPON: "武器",
};

// ============================================================
// フォーム
// ============================================================

const entrySchema = z.object({
  blueprint_id: z.string().min(1),
  target_type: z.enum(["MOBILE_SUIT", "WEAPON"]),
  target_id: z.string(),
  target_name: z.string(),
  faction: z.string(),
  is_standard_issue: z.boolean(),
  weight: z.number({ message: "Must be a number" }).int("Must be an integer").min(1, "Must be ≥ 1"),
  requires_win: z.boolean(),
});

export const dropTableFormSchema = z
  .object({
    name: z.string().min(1, "Name is required"),
    drop_rate: z.number({ message: "Must be a number" }).min(0, "Must be 0-1").max(1, "Must be 0-1"),
    win_rate_multiplier: z.number({ message: "Must be a number" }).min(1, "Must be ≥ 1"),
    entries: z.array(entrySchema),
  })
  .superRefine((values, ctx) => {
    const seen = new Set<string>();
    values.entries.forEach((entry, index) => {
      if (seen.has(entry.blueprint_id)) {
        ctx.addIssue({
          code: "custom",
          path: ["entries", index, "blueprint_id"],
          message: "同じ設計図がすでにテーブルにある",
        });
      }
      seen.add(entry.blueprint_id);
    });
  });

export type DropTableFormValues = z.infer<typeof dropTableFormSchema>;

export function toDropTableFormValues(detail: DropTableDetail): DropTableFormValues {
  return {
    name: detail.name,
    drop_rate: detail.drop_rate,
    win_rate_multiplier: detail.win_rate_multiplier,
    entries: detail.entries.map((entry) => ({ ...entry })),
  };
}

export function toDropTableUpdate(values: DropTableFormValues): DropTableUpdate {
  return {
    name: values.name,
    drop_rate: values.drop_rate,
    win_rate_multiplier: values.win_rate_multiplier,
    entries: values.entries.map(({ blueprint_id, weight, requires_win }) => ({
      blueprint_id,
      weight,
      requires_win,
    })),
  };
}

// ============================================================
// エントリーの追加
// ============================================================

/** backend の BlueprintService.blueprint_id_for と同じ規則で設計図IDを返す。 */
export function blueprintIdFor(
  targetType: BlueprintTargetSummary["target_type"],
  targetId: string
): string {
  return `${targetType.toLowerCase()}:${targetId}`;
}

export function entryFromSummary(summary: BlueprintTargetSummary): DropTableEntryDetail {
  return { ...summary, weight: 1, requires_win: false };
}

export function entryFromMobileSuit(ms: MasterMobileSuit): DropTableEntryDetail {
  return entryFromSummary({
    blueprint_id: blueprintIdFor("MOBILE_SUIT", ms.id),
    target_type: "MOBILE_SUIT",
    target_id: ms.id,
    target_name: ms.name_ja || ms.name,
    faction: ms.faction,
    is_standard_issue: ms.blueprint.is_standard_issue,
  });
}

export function entryFromWeapon(weapon: MasterWeapon): DropTableEntryDetail {
  return entryFromSummary({
    blueprint_id: blueprintIdFor("WEAPON", weapon.id),
    target_type: "WEAPON",
    target_id: weapon.id,
    target_name: weapon.name,
    faction: "",
    is_standard_issue: weapon.blueprint.is_standard_issue,
  });
}

// ============================================================
// 出現率（backend の DropService.roll と同じ計算）
// ============================================================

interface RateSettings {
  drop_rate: number;
  win_rate_multiplier: number;
}

interface RateEntry {
  weight: number;
  requires_win: boolean;
  faction: string;
}

/** 勝敗を反映したドロップ率を返す。backend の DropService.effective_drop_rate と同じ。 */
export function effectiveDropRate(settings: RateSettings, isWin: boolean): number {
  if (!isWin) return settings.drop_rate;
  return Math.min(settings.drop_rate * settings.win_rate_multiplier, 1);
}

/** パイロットの勢力で機体を扱えるかを返す。backend の is_available_to_faction と同じ。 */
export function isAvailableToFaction(pilotFaction: string, itemFaction: string): boolean {
  return !pilotFaction || !itemFaction || itemFaction === pilotFaction;
}

function isCandidate(entry: RateEntry, faction: DropFaction, isWin: boolean): boolean {
  if (entry.requires_win && !isWin) return false;
  return isAvailableToFaction(faction, entry.faction);
}

/**
 * 1回のバトルで各エントリーの設計図が出る確率を、エントリーと同じ順で返す。
 * 抽選対象外のエントリーは null。入力途中の不正な重みは 0 として扱う。
 */
export function dropChances(
  entries: RateEntry[],
  settings: RateSettings,
  isWin: boolean,
  faction: DropFaction
): (number | null)[] {
  const weightOf = (entry: RateEntry) =>
    Number.isFinite(entry.weight) && entry.weight > 0 ? entry.weight : 0;
  const candidates = entries.map((entry) => isCandidate(entry, faction, isWin));
  const totalWeight = entries.reduce(
    (sum, entry, i) => (candidates[i] ? sum + weightOf(entry) : sum),
    0
  );
  const rate = effectiveDropRate(settings, isWin);
  return entries.map((entry, i) => {
    if (!candidates[i]) return null;
    if (totalWeight === 0) return 0;
    return (rate * weightOf(entry)) / totalWeight;
  });
}

export function formatChance(chance: number | null): string {
  if (chance === null) return "—";
  if (!Number.isFinite(chance)) return "?";
  return `${(chance * 100).toFixed(2)}%`;
}

// ============================================================
// 入手手段の無い設計図
// ============================================================

/**
 * 編集中のエントリーを反映した、入手手段の無い設計図を返す。
 * 保存済みの一覧に、保存済みエントリーのうち要設計図のものを足し、編集中のエントリーを除く。
 */
export function unobtainableBlueprints(
  saved: DropTableDetail,
  currentBlueprintIds: string[]
): BlueprintTargetSummary[] {
  const current = new Set(currentBlueprintIds);
  const removedEntries: BlueprintTargetSummary[] = saved.entries
    .filter((entry) => !entry.is_standard_issue)
    .map((entry) => ({
      blueprint_id: entry.blueprint_id,
      target_type: entry.target_type,
      target_id: entry.target_id,
      target_name: entry.target_name,
      faction: entry.faction,
      is_standard_issue: entry.is_standard_issue,
    }));
  return [...saved.unobtainable_blueprints, ...removedEntries]
    .filter((summary) => !current.has(summary.blueprint_id))
    // backend と同じく設計図IDのコードポイント順に並べる。
    .sort((a, b) => (a.blueprint_id < b.blueprint_id ? -1 : a.blueprint_id > b.blueprint_id ? 1 : 0));
}
