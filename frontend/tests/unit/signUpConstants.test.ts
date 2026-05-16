import { describe, it, expect } from "vitest";
import {
  themeTextClass,
  themeLabelClass,
  themeBorderBgClass,
  BONUS_POINTS_TOTAL,
  STAT_KEYS,
  INITIAL_BONUS,
  FACTION_UNIT_NAME,
  PHASE_LABELS,
  type ThemeVariant,
} from "@/app/sign-up/[[...sign-up]]/_constants";

// ─────────────────────────────────────────────
// themeTextClass — 説明テキストの色クラス
// ─────────────────────────────────────────────
describe("themeTextClass", () => {
  it("accent のとき水色（#00f0ff）のクラスを返す", () => {
    expect(themeTextClass("accent")).toBe("text-[#00f0ff]/70");
  });

  it("secondary のときオレンジ（#ffb000）のクラスを返す", () => {
    expect(themeTextClass("secondary")).toBe("text-[#ffb000]/70");
  });

  it("accent と secondary で異なるクラスを返す", () => {
    expect(themeTextClass("accent")).not.toBe(themeTextClass("secondary"));
  });
});

// ─────────────────────────────────────────────
// themeLabelClass — ラベルテキストの色クラス
// ─────────────────────────────────────────────
describe("themeLabelClass", () => {
  it("accent のとき水色（#00f0ff）のクラスを返す", () => {
    expect(themeLabelClass("accent")).toBe("text-[#00f0ff]/80");
  });

  it("secondary のときオレンジ（#ffb000）のクラスを返す", () => {
    expect(themeLabelClass("secondary")).toBe("text-[#ffb000]/80");
  });

  it("themeTextClass より不透明度が高い（/80 > /70）", () => {
    // ラベルはテキストより若干強調される設計
    const label = themeLabelClass("accent");
    const text = themeTextClass("accent");
    expect(label).toContain("/80");
    expect(text).toContain("/70");
  });
});

// ─────────────────────────────────────────────
// themeBorderBgClass — ボーダー＋背景の複合クラス
// ─────────────────────────────────────────────
describe("themeBorderBgClass", () => {
  it("accent のとき水色のボーダーと背景クラスを返す", () => {
    const result = themeBorderBgClass("accent");
    expect(result).toContain("border-[#00f0ff]");
    expect(result).toContain("bg-[#00f0ff]");
  });

  it("secondary のときオレンジのボーダーと背景クラスを返す", () => {
    const result = themeBorderBgClass("secondary");
    expect(result).toContain("border-[#ffb000]");
    expect(result).toContain("bg-[#ffb000]");
  });

  it("accent と secondary で完全に異なるクラス文字列を返す", () => {
    expect(themeBorderBgClass("accent")).not.toBe(themeBorderBgClass("secondary"));
  });

  it("すべてのバリアントでボーダーと背景の両クラスを含む", () => {
    const variants: ThemeVariant[] = ["accent", "secondary"];
    for (const v of variants) {
      const result = themeBorderBgClass(v);
      expect(result).toMatch(/border-/);
      expect(result).toMatch(/bg-/);
    }
  });
});

// ─────────────────────────────────────────────
// 定数値の検証
// ─────────────────────────────────────────────
describe("定数値", () => {
  it("BONUS_POINTS_TOTAL は 5 である", () => {
    expect(BONUS_POINTS_TOTAL).toBe(5);
  });

  it("STAT_KEYS は DEX / INT / REF / TOU / LUK の5種類を含む", () => {
    expect(STAT_KEYS).toHaveLength(5);
    expect(STAT_KEYS).toContain("DEX");
    expect(STAT_KEYS).toContain("INT");
    expect(STAT_KEYS).toContain("REF");
    expect(STAT_KEYS).toContain("TOU");
    expect(STAT_KEYS).toContain("LUK");
  });

  it("INITIAL_BONUS はすべてのステータスが 0 である", () => {
    for (const key of STAT_KEYS) {
      expect(INITIAL_BONUS[key]).toBe(0);
    }
  });

  it("INITIAL_BONUS の合計は 0 である", () => {
    const total = Object.values(INITIAL_BONUS).reduce((a, b) => a + b, 0);
    expect(total).toBe(0);
  });

  it("FACTION_UNIT_NAME は FEDERATION と ZEON の2勢力を持つ", () => {
    expect(FACTION_UNIT_NAME.FEDERATION).toBeTruthy();
    expect(FACTION_UNIT_NAME.ZEON).toBeTruthy();
  });

  it("FACTION_UNIT_NAME の機体名は空文字でない", () => {
    expect(FACTION_UNIT_NAME.FEDERATION.length).toBeGreaterThan(0);
    expect(FACTION_UNIT_NAME.ZEON.length).toBeGreaterThan(0);
  });

  it("PHASE_LABELS は 5 フェーズ分のラベルを持つ", () => {
    expect(PHASE_LABELS).toHaveLength(5);
  });

  it("PHASE_LABELS のすべての要素が空文字でない", () => {
    for (const label of PHASE_LABELS) {
      expect(label.length).toBeGreaterThan(0);
    }
  });
});
