import { describe, it, expect } from "vitest";
import {
  blueprintIdFor,
  dropChances,
  dropTableFormSchema,
  effectiveDropRate,
  entryFromMobileSuit,
  entryFromWeapon,
  formatChance,
  isAvailableToFaction,
  toDropTableFormValues,
  toDropTableUpdate,
  unobtainableBlueprints,
} from "@/lib/dropTable";
import {
  BlueprintTargetSummary,
  DropTableDetail,
  DropTableEntryDetail,
  MasterMobileSuit,
  MasterWeapon,
} from "@/types/admin";

function entry(overrides: Partial<DropTableEntryDetail>): DropTableEntryDetail {
  return {
    blueprint_id: "mobile_suit:dom",
    target_type: "MOBILE_SUIT",
    target_id: "dom",
    target_name: "Dom",
    faction: "",
    is_standard_issue: false,
    weight: 1,
    requires_win: false,
    ...overrides,
  };
}

function summary(blueprintId: string, isStandardIssue = false): BlueprintTargetSummary {
  return {
    blueprint_id: blueprintId,
    target_type: "MOBILE_SUIT",
    target_id: blueprintId.split(":")[1],
    target_name: blueprintId,
    faction: "",
    is_standard_issue: isStandardIssue,
  };
}

describe("effectiveDropRate", () => {
  it("敗北時は drop_rate、勝利時は倍率を掛ける", () => {
    const settings = { drop_rate: 0.3, win_rate_multiplier: 1.5 };
    expect(effectiveDropRate(settings, false)).toBe(0.3);
    expect(effectiveDropRate(settings, true)).toBeCloseTo(0.45);
  });

  it("勝利時のドロップ率は1を上限とする", () => {
    expect(effectiveDropRate({ drop_rate: 0.6, win_rate_multiplier: 2 }, true)).toBe(1);
  });
});

describe("isAvailableToFaction", () => {
  it("共通機体はどの勢力でも扱える", () => {
    expect(isAvailableToFaction("ZEON", "")).toBe(true);
  });

  it("別勢力の機体は扱えない", () => {
    expect(isAvailableToFaction("ZEON", "FEDERATION")).toBe(false);
    expect(isAvailableToFaction("ZEON", "ZEON")).toBe(true);
  });
});

describe("dropChances", () => {
  const settings = { drop_rate: 0.4, win_rate_multiplier: 2 };

  it("ドロップ率 × 重み ÷ 抽選対象の重みの合計になる", () => {
    const entries = [entry({ weight: 3 }), entry({ weight: 1 })];
    const chances = dropChances(entries, settings, false, "ZEON");
    expect(chances[0]).toBeCloseTo(0.3);
    expect(chances[1]).toBeCloseTo(0.1);
  });

  it("敗北時は勝利時のみのエントリーを除き、残りの確率が上がる", () => {
    const entries = [entry({ weight: 1, requires_win: true }), entry({ weight: 1 })];
    expect(dropChances(entries, settings, false, "ZEON")).toEqual([null, 0.4]);
    const win = dropChances(entries, settings, true, "ZEON");
    expect(win[0]).toBeCloseTo(0.4);
    expect(win[1]).toBeCloseTo(0.4);
  });

  it("勢力で扱えない機体を除き、残りの確率が上がる", () => {
    const entries = [
      entry({ faction: "FEDERATION", weight: 1 }),
      entry({ faction: "ZEON", weight: 1 }),
      entry({ target_type: "WEAPON", faction: "", weight: 2 }),
    ];
    const zeon = dropChances(entries, settings, false, "ZEON");
    expect(zeon[0]).toBeNull();
    expect(zeon[1]).toBeCloseTo(0.4 / 3);
    expect(zeon[2]).toBeCloseTo((0.4 * 2) / 3);
    const federation = dropChances(entries, settings, false, "FEDERATION");
    expect(federation[0]).toBeCloseTo(0.4 / 3);
    expect(federation[1]).toBeNull();
  });

  it("入力途中の不正な重みは0として扱う", () => {
    const entries = [entry({ weight: Number.NaN }), entry({ weight: 1 })];
    expect(dropChances(entries, settings, false, "ZEON")).toEqual([0, 0.4]);
    expect(dropChances([entry({ weight: 0 })], settings, false, "ZEON")).toEqual([0]);
  });
});

describe("formatChance", () => {
  it("抽選対象外は「—」、それ以外は小数2桁の%で表示する", () => {
    expect(formatChance(null)).toBe("—");
    expect(formatChance(0.12345)).toBe("12.35%");
    expect(formatChance(Number.NaN)).toBe("?");
  });
});

describe("dropTableFormSchema", () => {
  const valid = {
    name: "定期バトル",
    drop_rate: 0.3,
    win_rate_multiplier: 1.5,
    entries: [entry({})],
  };

  it("正しい値とエントリー0件を受け入れる", () => {
    expect(dropTableFormSchema.safeParse(valid).success).toBe(true);
    expect(dropTableFormSchema.safeParse({ ...valid, entries: [] }).success).toBe(true);
  });

  it.each([
    ["drop_rate が負", { drop_rate: -0.1 }],
    ["drop_rate が1超", { drop_rate: 1.1 }],
    ["倍率が1未満", { win_rate_multiplier: 0.9 }],
    ["重みが0", { entries: [entry({ weight: 0 })] }],
    ["重みが小数", { entries: [entry({ weight: 1.5 })] }],
    ["名前が空", { name: "" }],
  ])("%s はエラー", (_label, overrides) => {
    expect(dropTableFormSchema.safeParse({ ...valid, ...overrides }).success).toBe(false);
  });

  it("同じ設計図のエントリーは2つ目をエラーにする", () => {
    const result = dropTableFormSchema.safeParse({ ...valid, entries: [entry({}), entry({})] });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0].path).toEqual(["entries", 1, "blueprint_id"]);
  });
});

describe("toDropTableUpdate", () => {
  it("エントリーは保存に使う項目だけを送る", () => {
    const detail: DropTableDetail = {
      id: 1,
      name: "定期バトル",
      drop_rate: 0.3,
      win_rate_multiplier: 1.5,
      entries: [entry({ weight: 2, requires_win: true })],
      unobtainable_blueprints: [],
    };
    expect(toDropTableUpdate(toDropTableFormValues(detail))).toEqual({
      name: "定期バトル",
      drop_rate: 0.3,
      win_rate_multiplier: 1.5,
      entries: [{ blueprint_id: "mobile_suit:dom", weight: 2, requires_win: true }],
    });
  });
});

describe("エントリーの追加", () => {
  it("設計図IDは backend と同じ規則で決まる", () => {
    expect(blueprintIdFor("MOBILE_SUIT", "rx_78_2")).toBe("mobile_suit:rx_78_2");
    expect(blueprintIdFor("WEAPON", "beam_rifle")).toBe("weapon:beam_rifle");
  });

  it("機体マスターから、日本語名・勢力・標準配備かを引き継ぐ", () => {
    const ms = {
      id: "gelgoog",
      name: "Gelgoog",
      name_ja: "ゲルググ",
      faction: "ZEON",
      blueprint: { is_standard_issue: false, duplicate_credit_value: 0 },
    } as MasterMobileSuit;
    expect(entryFromMobileSuit(ms)).toEqual({
      blueprint_id: "mobile_suit:gelgoog",
      target_type: "MOBILE_SUIT",
      target_id: "gelgoog",
      target_name: "ゲルググ",
      faction: "ZEON",
      is_standard_issue: false,
      weight: 1,
      requires_win: false,
    });
  });

  it("武器マスターには勢力が無い", () => {
    const weapon = {
      id: "beam_rifle",
      name: "Beam Rifle",
      blueprint: { is_standard_issue: true, duplicate_credit_value: 0 },
    } as MasterWeapon;
    expect(entryFromWeapon(weapon)).toMatchObject({
      blueprint_id: "weapon:beam_rifle",
      target_type: "WEAPON",
      faction: "",
      is_standard_issue: true,
    });
  });
});

describe("unobtainableBlueprints", () => {
  const saved: DropTableDetail = {
    id: 1,
    name: "定期バトル",
    drop_rate: 0.3,
    win_rate_multiplier: 1.5,
    entries: [
      entry({ blueprint_id: "mobile_suit:gelgoog", is_standard_issue: false }),
      entry({ blueprint_id: "mobile_suit:dom", is_standard_issue: true }),
    ],
    unobtainable_blueprints: [summary("weapon:beam_rifle"), summary("mobile_suit:gundam")],
  };

  it("保存済みの一覧から、編集中に追加した設計図を除く", () => {
    const result = unobtainableBlueprints(saved, [
      "mobile_suit:gelgoog",
      "mobile_suit:dom",
      "mobile_suit:gundam",
    ]);
    expect(result.map((s) => s.blueprint_id)).toEqual(["weapon:beam_rifle"]);
  });

  it("編集中に外した要設計図を加える。標準配備は加えない", () => {
    const result = unobtainableBlueprints(saved, []);
    expect(result.map((s) => s.blueprint_id)).toEqual([
      "mobile_suit:gelgoog",
      "mobile_suit:gundam",
      "weapon:beam_rifle",
    ]);
    expect(result[0]).not.toHaveProperty("weight");
  });
});
