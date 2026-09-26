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
    });
    expect(result.success).toBe(true);
  });

  it("換金額の空欄（null）を受け入れる", () => {
    const result = blueprintFormSchema.safeParse({
      is_standard_issue: true,
      duplicate_credit_value: null,
    });
    expect(result.success).toBe(true);
  });

  it("負の換金額はエラー", () => {
    const result = blueprintFormSchema.safeParse({
      is_standard_issue: true,
      duplicate_credit_value: -1,
    });
    expect(result.success).toBe(false);
    expect(result.error?.issues.some((i) => i.path.includes("duplicate_credit_value"))).toBe(true);
  });

  it("小数の換金額はエラー", () => {
    const result = blueprintFormSchema.safeParse({
      is_standard_issue: true,
      duplicate_credit_value: 10.5,
    });
    expect(result.success).toBe(false);
  });
});

describe("toBlueprintFormValues", () => {
  it("新規作成では標準配備・換金額は空欄になる", () => {
    expect(toBlueprintFormValues(null)).toEqual({
      is_standard_issue: true,
      duplicate_credit_value: null,
    });
  });

  it("編集では現在の設定を入れる", () => {
    expect(
      toBlueprintFormValues({ is_standard_issue: false, duplicate_credit_value: 300 })
    ).toEqual({ is_standard_issue: false, duplicate_credit_value: 300 });
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
    });
  });
});

describe("applyBlueprintInput", () => {
  const current = { is_standard_issue: true, duplicate_credit_value: 100 };

  it("指定した項目だけを上書きする", () => {
    expect(
      applyBlueprintInput(current, { is_standard_issue: false, duplicate_credit_value: null })
    ).toEqual({ is_standard_issue: false, duplicate_credit_value: 100 });
  });

  it("入力が無ければ現在の設定を返す", () => {
    expect(applyBlueprintInput(current, undefined)).toEqual(current);
  });
});

describe("matchesBlueprintFilter", () => {
  const standard = { is_standard_issue: true, duplicate_credit_value: 0 };
  const required = { is_standard_issue: false, duplicate_credit_value: 0 };

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
