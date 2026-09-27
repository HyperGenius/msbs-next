import { describe, it, expect } from "vitest";
import { BlueprintCollectionItem } from "@/types/battle";
import {
  collectionProgress,
  collectionStatus,
  filterAndSortCollection,
  formatTheater,
  obtainabilityOf,
} from "@/utils/blueprintCollection";

/** 未所持・入手先ありの設計図を作るヘルパー */
const item = (overrides: Partial<BlueprintCollectionItem> = {}): BlueprintCollectionItem => ({
  blueprint_id: "mobile_suit:gelgoog",
  target_type: "MOBILE_SUIT",
  target_id: "gelgoog",
  target_name: "ゲルググ",
  faction: "ZEON",
  is_standard_issue: false,
  is_owned: false,
  acquired_at: null,
  source: null,
  is_available_to_faction: true,
  obtainable_theaters: [{ label: "全戦域", requires_win: false }],
  tech_requirements: [],
  ...overrides,
});

const owned = item({
  blueprint_id: "mobile_suit:dom",
  target_name: "ドム",
  is_owned: true,
  acquired_at: "2026-09-26T00:00:00Z",
  source: "DROP",
  obtainable_theaters: [],
});
const standard = item({
  blueprint_id: "mobile_suit:zaku_ii",
  target_name: "ザクII",
  is_standard_issue: true,
  obtainable_theaters: [],
});

describe("collectionStatus", () => {
  it("所持・未所持・標準配備を区別する", () => {
    expect(collectionStatus(item())).toBe("unowned");
    expect(collectionStatus(owned)).toBe("owned");
    expect(collectionStatus(standard)).toBe("standard");
  });

  it("標準配備品は所持記録があっても標準配備とする", () => {
    expect(collectionStatus({ ...standard, is_owned: true })).toBe("standard");
  });
});

describe("filterAndSortCollection", () => {
  const gouf = item({ blueprint_id: "mobile_suit:gouf", target_name: "グフ" });
  const items = [standard, owned, item(), gouf];

  it("未所持・所持・標準配備の順、同じ状態の中は名前順に並べる", () => {
    expect(filterAndSortCollection(items, "all").map((i) => i.target_name)).toEqual([
      "グフ",
      "ゲルググ",
      "ドム",
      "ザクII",
    ]);
  });

  it("状態で絞り込む", () => {
    expect(filterAndSortCollection(items, "unowned")).toHaveLength(2);
    expect(filterAndSortCollection(items, "owned")).toEqual([owned]);
    expect(filterAndSortCollection(items, "standard")).toEqual([standard]);
  });

  it("元の配列を並べ替えない", () => {
    const original = [...items];
    filterAndSortCollection(items, "all");
    expect(items).toEqual(original);
  });
});

describe("collectionProgress", () => {
  it("標準配備を除いた設計図を分母にする", () => {
    expect(collectionProgress([standard, owned, item()])).toEqual({
      owned: 1,
      total: 2,
      percent: 50,
    });
  });

  it("全件所持のときだけ100%になるよう切り捨てる", () => {
    const items = [owned, owned, item()];
    expect(collectionProgress(items).percent).toBe(66);
  });

  it("対象が無ければ percent は null", () => {
    expect(collectionProgress([standard])).toEqual({ owned: 0, total: 0, percent: null });
  });
});

describe("obtainabilityOf", () => {
  it("所持済み・標準配備には入手先を出さない", () => {
    expect(obtainabilityOf(owned)).toBeNull();
    expect(obtainabilityOf(standard)).toBeNull();
  });

  it("勢力外の機体は入手できない", () => {
    expect(
      obtainabilityOf(item({ is_available_to_faction: false, obtainable_theaters: [] })),
    ).toEqual({ kind: "other_faction" });
  });

  it("入手先が無ければ入手できない", () => {
    expect(obtainabilityOf(item({ obtainable_theaters: [] }))).toEqual({ kind: "unavailable" });
  });

  it("入手できる戦域を返す", () => {
    expect(obtainabilityOf(item())).toEqual({
      kind: "theaters",
      theaters: [{ label: "全戦域", requires_win: false }],
    });
  });
});

describe("formatTheater", () => {
  it("勝利時のみなら注記を付ける", () => {
    expect(formatTheater({ label: "全戦域", requires_win: false })).toBe("全戦域");
    expect(formatTheater({ label: "全戦域", requires_win: true })).toBe("全戦域（勝利時のみ）");
  });
});
