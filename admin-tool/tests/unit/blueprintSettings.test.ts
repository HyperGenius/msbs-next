import { describe, it, expect } from "vitest";
import {
  blueprintFormSchema,
  nullableNumberOptions,
  toBlueprintFormValues,
} from "@/components/admin/BlueprintSettingsFields";
import {
  applyBlueprintInput,
  defaultBlueprintSettings,
  matchesBlueprintFilter,
} from "@/lib/blueprint";

describe("blueprintFormSchema", () => {
  it("標準配備フラグと 0 以上の整数の換金額を受け入れる", () => {
    const result = blueprintFormSchema.safeParse({
      is_standard_issue: false,
      duplicate_credit_value: 0,
      tech_requirements: [],
    });
    expect(result.success).toBe(true);
  });

  it("換金額の空欄（null）を受け入れる", () => {
    const result = blueprintFormSchema.safeParse({
      is_standard_issue: true,
      duplicate_credit_value: null,
      tech_requirements: [],
    });
    expect(result.success).toBe(true);
  });

  it("負の換金額はエラー", () => {
    const result = blueprintFormSchema.safeParse({
      is_standard_issue: true,
      duplicate_credit_value: -1,
      tech_requirements: [],
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("duplicate_credit_value"))).toBe(true);
  });

  it("小数の換金額はエラー", () => {
    const result = blueprintFormSchema.safeParse({
      is_standard_issue: true,
      duplicate_credit_value: 10.5,
      tech_requirements: [],
    });
    expect(result.success).toBe(false);
  });

  it("必要な技術Lvは技術の選択と1以上のLvが必要で、同じ技術は2つ置けない", () => {
    const base = { is_standard_issue: false, duplicate_credit_value: 0 };
    const psycommu = { tech_id: "psycommu_tech", required_lv: 2 };
    expect(blueprintFormSchema.safeParse({ ...base, tech_requirements: [psycommu] }).success).toBe(true);
    expect(
      blueprintFormSchema.safeParse({ ...base, tech_requirements: [{ tech_id: "", required_lv: 1 }] })
        .success
    ).toBe(false);
    expect(
      blueprintFormSchema.safeParse({ ...base, tech_requirements: [{ ...psycommu, required_lv: 0 }] })
        .success
    ).toBe(false);
    const duplicated = blueprintFormSchema.safeParse({ ...base, tech_requirements: [psycommu, psycommu] });
    expect(duplicated.success).toBe(false);
    expect(duplicated.error?.issues[0].path).toEqual(["tech_requirements", 1, "tech_id"]);
  });
});

describe("toBlueprintFormValues", () => {
  it("新規作成では標準配備・換金額は空欄になる", () => {
    expect(toBlueprintFormValues(null)).toEqual({
      is_standard_issue: true,
      duplicate_credit_value: null,
      tech_requirements: [],
    });
  });

  it("編集では現在の設定を入れる", () => {
    const requirements = [{ tech_id: "psycommu_tech", required_lv: 2 }];
    const values = toBlueprintFormValues({
      is_standard_issue: false,
      duplicate_credit_value: 300,
      tech_requirements: requirements,
    });
    expect(values).toEqual({
      is_standard_issue: false,
      duplicate_credit_value: 300,
      tech_requirements: requirements,
    });
    // フォームでの編集が元の設定を書き換えないよう、行を複製する。
    expect(values.tech_requirements[0]).not.toBe(requirements[0]);
  });
});

describe("nullableNumberOptions", () => {
  it("空欄を null、数字を数値として読む", () => {
    expect(nullableNumberOptions.setValueAs("")).toBeNull();
    expect(nullableNumberOptions.setValueAs("250")).toBe(250);
  });
});

describe("defaultBlueprintSettings", () => {
  it("標準配備・換金額は価格の20%（切り捨て）になる", () => {
    expect(defaultBlueprintSettings(1234)).toEqual({
      is_standard_issue: true,
      duplicate_credit_value: 246,
      tech_requirements: [],
    });
  });
});

describe("applyBlueprintInput", () => {
  const current = {
    is_standard_issue: true,
    duplicate_credit_value: 100,
    tech_requirements: [{ tech_id: "psycommu_tech", required_lv: 1 }],
  };

  it("指定した項目だけを上書きする", () => {
    expect(
      applyBlueprintInput(current, { is_standard_issue: false, duplicate_credit_value: null })
    ).toEqual({ ...current, is_standard_issue: false });
  });

  it("必要な技術Lvは指定すると置き換える", () => {
    expect(applyBlueprintInput(current, { tech_requirements: [] }).tech_requirements).toEqual([]);
  });

  it("入力が無ければ現在の設定を返す", () => {
    expect(applyBlueprintInput(current, undefined)).toEqual(current);
  });
});

describe("matchesBlueprintFilter", () => {
  const standard = { is_standard_issue: true };
  const required = { is_standard_issue: false };

  it("標準配備・要設計図で絞り込める", () => {
    expect(matchesBlueprintFilter(standard, "standard")).toBe(true);
    expect(matchesBlueprintFilter(required, "standard")).toBe(false);
    expect(matchesBlueprintFilter(standard, "required")).toBe(false);
    expect(matchesBlueprintFilter(required, "required")).toBe(true);
  });

  it("すべてなら絞り込まない", () => {
    expect(matchesBlueprintFilter(standard, "all")).toBe(true);
    expect(matchesBlueprintFilter(required, "all")).toBe(true);
  });
});
