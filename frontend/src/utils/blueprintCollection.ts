/* frontend/src/utils/blueprintCollection.ts */
import { BlueprintCollectionItem, BlueprintSource, ObtainableTheater } from "@/types/battle";

/** 図鑑での設計図の状態 */
export type CollectionStatus = "unowned" | "owned" | "standard";

/** 図鑑の状態の絞り込み */
export type CollectionFilter = "all" | CollectionStatus;

export const COLLECTION_STATUS_LABELS: Record<CollectionStatus, string> = {
  unowned: "未所持",
  owned: "所持",
  standard: "標準配備",
};

export const BLUEPRINT_SOURCE_LABELS: Record<BlueprintSource, string> = {
  DROP: "ドロップ",
  MIGRATION: "導入時の付与",
};

export const FACTION_LABELS: Record<string, string> = {
  FEDERATION: "地球連邦軍",
  ZEON: "ジオン公国軍",
};

export const OTHER_FACTION_MESSAGE = "あなたの勢力では入手できません";
export const UNAVAILABLE_MESSAGE = "現在は入手できません";

const WIN_ONLY_SUFFIX = "（勝利時のみ）";

// 同じ状態の中は名前順に並べる。未所持を先頭にして次に狙う設計図を探しやすくする。
const STATUS_ORDER: Record<CollectionStatus, number> = {
  unowned: 0,
  owned: 1,
  standard: 2,
};

/** 設計図の図鑑での状態を返す。標準配備品は所持記録があっても標準配備とする */
export function collectionStatus(item: BlueprintCollectionItem): CollectionStatus {
  if (item.is_standard_issue) return "standard";
  return item.is_owned ? "owned" : "unowned";
}

/** 状態で絞り込み、未所持・所持・標準配備の順、同じ状態の中は名前順に並べる */
export function filterAndSortCollection(
  items: BlueprintCollectionItem[],
  filter: CollectionFilter,
): BlueprintCollectionItem[] {
  return items
    .filter((item) => filter === "all" || collectionStatus(item) === filter)
    .sort(
      (a, b) =>
        STATUS_ORDER[collectionStatus(a)] - STATUS_ORDER[collectionStatus(b)] ||
        a.target_name.localeCompare(b.target_name, "ja"),
    );
}

/** 収集率。分母は標準配備を除いた設計図の数 */
export interface CollectionProgress {
  owned: number;
  total: number;
  /** 0〜100 の整数（切り捨て）。対象が無ければ null */
  percent: number | null;
}

/** 設計図の一覧から収集率を求める */
export function collectionProgress(items: BlueprintCollectionItem[]): CollectionProgress {
  const targets = items.filter((item) => !item.is_standard_issue);
  const owned = targets.filter((item) => item.is_owned).length;
  const total = targets.length;
  // 100% 表示は全件所持のときだけにするため、四捨五入ではなく切り捨てる。
  const percent = total === 0 ? null : Math.floor((owned / total) * 100);
  return { owned, total, percent };
}

/** 未所持の設計図の入手先の表示。所持済み・標準配備なら null */
export type Obtainability =
  | { kind: "theaters"; theaters: ObtainableTheater[] }
  | { kind: "other_faction" }
  | { kind: "unavailable" };

/** 未所持の設計図について、入手先の表示内容を返す */
export function obtainabilityOf(item: BlueprintCollectionItem): Obtainability | null {
  if (collectionStatus(item) !== "unowned") return null;
  if (!item.is_available_to_faction) return { kind: "other_faction" };
  if (item.obtainable_theaters.length === 0) return { kind: "unavailable" };
  return { kind: "theaters", theaters: item.obtainable_theaters };
}

/** 入手できる戦域の表示名を返す。勝利時のみなら注記を付ける */
export function formatTheater(theater: ObtainableTheater): string {
  return theater.requires_win ? `${theater.label}${WIN_ONLY_SUFFIX}` : theater.label;
}
