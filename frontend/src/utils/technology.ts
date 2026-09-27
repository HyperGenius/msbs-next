/* frontend/src/utils/technology.ts */
import {
  LootItem,
  PlayerTechnologyProgress,
  TechFragmentLootItem,
  TechRequirementStatus,
} from "@/types/battle";

/** 足りない技術Lvの表示。backend の format_missing_tech と同じ文言 */
export function formatMissingTech(requirement: TechRequirementStatus): string {
  return `${requirement.tech_name} Lv${requirement.required_lv} が必要（現在 Lv${requirement.current_lv}）`;
}

/** 必要な技術Lvのうち、現在Lvが足りないものを返す */
export function unmetTechRequirements(
  requirements: TechRequirementStatus[],
): TechRequirementStatus[] {
  return requirements.filter((r) => r.current_lv < r.required_lv);
}

/**
 * 次のLvまでの進捗（0〜100 の整数、切り捨て）。
 * 累計数を次のLvの閾値で割る。最大Lvなら 100。
 */
export function techProgressPercent(
  progress: Pick<PlayerTechnologyProgress, "fragment_count" | "next_level_threshold">,
): number {
  if (progress.next_level_threshold === null) return 100;
  return Math.floor((progress.fragment_count / progress.next_level_threshold) * 100);
}

/** 技術断片の戦利品の説明文 */
export function techFragmentLootMessage(item: TechFragmentLootItem): string {
  if (item.credits_awarded > 0) {
    return `最大Lvのため +${item.credits_awarded.toLocaleString()} C に換金`;
  }
  const levelText = item.level >= item.max_level ? `Lv${item.level}（最大）` : `Lv${item.level}`;
  if (item.is_level_up) {
    return `${levelText} に上昇！ 累計 ${item.fragment_count} 個`;
  }
  return `累計 ${item.fragment_count} 個・次のLvまであと ${item.fragments_to_next_level ?? 0} 個`;
}

/** 入手演出を再生する戦利品か（設計図の新規入手・技術Lvの上昇） */
export function isHighlightedLoot(item: LootItem): boolean {
  return item.kind === "BLUEPRINT" ? item.is_new : item.is_level_up;
}

/** 一覧の key に使う戦利品のID */
export function lootKey(item: LootItem): string {
  return item.kind === "BLUEPRINT" ? item.blueprint_id : `tech:${item.tech_id}`;
}

/** バトル履歴の一覧に付けるバッジの表示 */
export type LootBadgeInfo =
  | { tone: "highlight"; label: "NEW" | "LV UP" }
  | { tone: "normal"; label: string };

/**
 * 戦利品のバッジの表示を返す。戦利品が無ければ null。
 * 設計図の新規入手 → 技術Lvの上昇 → 換金額 → 技術断片の入手の順に優先する。
 */
export function lootBadgeOf(loot: LootItem[] | null | undefined): LootBadgeInfo | null {
  if (!loot || loot.length === 0) return null;
  if (loot.some((item) => item.kind === "BLUEPRINT" && item.is_new)) {
    return { tone: "highlight", label: "NEW" };
  }
  if (loot.some((item) => item.kind === "TECH_FRAGMENT" && item.is_level_up)) {
    return { tone: "highlight", label: "LV UP" };
  }
  const credits = loot.reduce((sum, item) => sum + item.credits_awarded, 0);
  if (credits > 0) return { tone: "normal", label: `+${credits.toLocaleString()} C` };
  return { tone: "normal", label: "+断片" };
}
