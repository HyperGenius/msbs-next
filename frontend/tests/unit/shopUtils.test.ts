import { describe, it, expect } from "vitest";
import { getBlueprintBadgeKind, isPurchasable } from "@/app/shop/utils";

const standardIssue = { is_standard_issue: true, is_unlocked: true, unlock_hint: null };
const blueprintOwned = { is_standard_issue: false, is_unlocked: true, unlock_hint: null };
const locked = {
  is_standard_issue: false,
  is_unlocked: false,
  unlock_hint: "バトルで設計図を入手すると購入できます",
};

describe("getBlueprintBadgeKind", () => {
  it("標準配備品にはバッジを付けない", () => {
    expect(getBlueprintBadgeKind(standardIssue)).toBeNull();
  });

  it("設計図で解放済みの商品は設計図所持バッジを付ける", () => {
    expect(getBlueprintBadgeKind(blueprintOwned)).toBe("blueprint_owned");
  });

  it("未解放の商品は未解放バッジを付ける", () => {
    expect(getBlueprintBadgeKind(locked)).toBe("locked");
  });
});

describe("isPurchasable", () => {
  it("解放済みで所持金が足りていれば購入できる", () => {
    expect(isPurchasable({ ...standardIssue, price: 500 }, 500)).toBe(true);
    expect(isPurchasable({ ...blueprintOwned, price: 500 }, 1000)).toBe(true);
  });

  it("所持金が足りなければ購入できない", () => {
    expect(isPurchasable({ ...standardIssue, price: 500 }, 499)).toBe(false);
  });

  it("未解放なら所持金が足りていても購入できない", () => {
    expect(isPurchasable({ ...locked, price: 500 }, 10000)).toBe(false);
  });
});
