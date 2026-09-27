import { describe, it, expect } from "vitest";
import { BlueprintLootItem, TechFragmentLootItem } from "@/types/battle";
import {
  formatMissingTech,
  isHighlightedLoot,
  lootBadgeOf,
  lootKey,
  techFragmentLootMessage,
  techProgressPercent,
  unmetTechRequirements,
} from "@/utils/technology";

const psycommu = { tech_id: "psycommu_tech", tech_name: "サイコミュ技術" };

const blueprint = (overrides: Partial<BlueprintLootItem> = {}): BlueprintLootItem => ({
  kind: "BLUEPRINT",
  blueprint_id: "mobile_suit:gelgoog",
  target_type: "MOBILE_SUIT",
  target_id: "gelgoog",
  target_name: "ゲルググ",
  is_new: false,
  credits_awarded: 300,
  ...overrides,
});

const fragment = (overrides: Partial<TechFragmentLootItem> = {}): TechFragmentLootItem => ({
  kind: "TECH_FRAGMENT",
  tech_id: "psycommu_tech",
  target_name: "サイコミュ技術",
  fragment_count: 5,
  level: 1,
  max_level: 3,
  is_level_up: false,
  fragments_to_next_level: 3,
  credits_awarded: 0,
  ...overrides,
});

describe("formatMissingTech", () => {
  it("backend と同じ文言で必要Lvと現在Lvを示す", () => {
    expect(formatMissingTech({ ...psycommu, required_lv: 2, current_lv: 1 })).toBe(
      "サイコミュ技術 Lv2 が必要（現在 Lv1）",
    );
  });
});

describe("unmetTechRequirements", () => {
  it("現在Lvが必要Lvに届かないものだけを返す", () => {
    const met = { ...psycommu, required_lv: 1, current_lv: 1 };
    const unmet = { ...psycommu, tech_id: "beam_generator_tech", required_lv: 2, current_lv: 1 };
    expect(unmetTechRequirements([met, unmet])).toEqual([unmet]);
  });
});

describe("techProgressPercent", () => {
  it("累計数を次のLvの閾値で割り、切り捨てる", () => {
    expect(techProgressPercent({ fragment_count: 5, next_level_threshold: 8 })).toBe(62);
    expect(techProgressPercent({ fragment_count: 0, next_level_threshold: 3 })).toBe(0);
  });

  it("最大Lvなら 100", () => {
    expect(techProgressPercent({ fragment_count: 15, next_level_threshold: null })).toBe(100);
  });
});

describe("techFragmentLootMessage", () => {
  it("通常は累計数と次のLvまでの残りを示す", () => {
    expect(techFragmentLootMessage(fragment())).toBe("累計 5 個・次のLvまであと 3 個");
  });

  it("Lvが上がったら上昇後のLvを示す", () => {
    expect(
      techFragmentLootMessage(fragment({ fragment_count: 8, level: 2, is_level_up: true })),
    ).toBe("Lv2 に上昇！ 累計 8 個");
  });

  it("最大Lvに到達したら最大と示す", () => {
    expect(
      techFragmentLootMessage(
        fragment({ fragment_count: 15, level: 3, is_level_up: true, fragments_to_next_level: null }),
      ),
    ).toBe("Lv3（最大） に上昇！ 累計 15 個");
  });

  it("最大Lv後の換金は換金額を示す", () => {
    expect(
      techFragmentLootMessage(
        fragment({ level: 3, fragments_to_next_level: null, credits_awarded: 500 }),
      ),
    ).toBe("最大Lvのため +500 C に換金");
  });
});

describe("isHighlightedLoot / lootKey", () => {
  it("設計図の新規入手と技術Lvの上昇を強調する", () => {
    expect(isHighlightedLoot(blueprint({ is_new: true }))).toBe(true);
    expect(isHighlightedLoot(blueprint())).toBe(false);
    expect(isHighlightedLoot(fragment({ is_level_up: true }))).toBe(true);
    expect(isHighlightedLoot(fragment())).toBe(false);
  });

  it("設計図と技術断片で key が重ならない", () => {
    expect(lootKey(blueprint())).toBe("mobile_suit:gelgoog");
    expect(lootKey(fragment())).toBe("tech:psycommu_tech");
  });
});

describe("lootBadgeOf", () => {
  it("戦利品が無ければ null", () => {
    expect(lootBadgeOf(null)).toBeNull();
    expect(lootBadgeOf([])).toBeNull();
  });

  it("設計図の新規入手を最優先する", () => {
    expect(lootBadgeOf([fragment({ is_level_up: true }), blueprint({ is_new: true })])).toEqual({
      tone: "highlight",
      label: "NEW",
    });
  });

  it("技術Lvの上昇は LV UP", () => {
    expect(lootBadgeOf([fragment({ is_level_up: true })])).toEqual({
      tone: "highlight",
      label: "LV UP",
    });
  });

  it("換金のみなら換金額の合計", () => {
    expect(lootBadgeOf([blueprint(), fragment({ credits_awarded: 500 })])).toEqual({
      tone: "normal",
      label: "+800 C",
    });
  });

  it("Lvの上がらない技術断片だけなら断片の入手を示す", () => {
    expect(lootBadgeOf([fragment()])).toEqual({ tone: "normal", label: "+断片" });
  });
});
