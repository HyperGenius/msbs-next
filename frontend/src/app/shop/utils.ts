import { BlueprintUnlockState } from "@/types/battle";

/** ショップ商品に付けるバッジの種類 */
export type BlueprintBadgeKind = "locked" | "blueprint_owned";

/** 解放状態に応じたバッジの種類を返す。標準配備品にはバッジを付けない */
export function getBlueprintBadgeKind(listing: BlueprintUnlockState): BlueprintBadgeKind | null {
  if (!listing.is_unlocked) return "locked";
  if (!listing.is_standard_issue) return "blueprint_owned";
  return null;
}

/** 解放済みで、所持金が足りている商品か */
export function isPurchasable(listing: BlueprintUnlockState & { price: number }, credits: number): boolean {
  return listing.is_unlocked && credits >= listing.price;
}
