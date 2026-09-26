import { MasterBlueprintSettings, MasterBlueprintSettingsInput } from "@/types/admin";

// backend の BlueprintService.DUPLICATE_CREDIT_RATIO と同じ値。
// 新規作成時の初期値の表示と楽観的更新にだけ使う。保存される値は backend が決める。
const DUPLICATE_CREDIT_RATIO = 0.2;

export type BlueprintFilter = "all" | "standard" | "required";

export const BLUEPRINT_FILTER_LABELS: Record<BlueprintFilter, string> = {
  all: "設計図: すべて",
  standard: "標準配備のみ",
  required: "要設計図のみ",
};

/** 設計図マスターを新規作成するときの初期値を返す。 */
export function defaultBlueprintSettings(price: number): MasterBlueprintSettings {
  return {
    is_standard_issue: true,
    duplicate_credit_value: Math.floor(price * DUPLICATE_CREDIT_RATIO),
  };
}

/** 保存リクエストを現在の設定に重ねた結果を返す。未指定（null・undefined）の項目は現在の値のまま。 */
export function applyBlueprintInput(
  current: MasterBlueprintSettings,
  input: MasterBlueprintSettingsInput | undefined
): MasterBlueprintSettings {
  return {
    is_standard_issue: input?.is_standard_issue ?? current.is_standard_issue,
    duplicate_credit_value: input?.duplicate_credit_value ?? current.duplicate_credit_value,
  };
}

export function matchesBlueprintFilter(
  blueprint: MasterBlueprintSettings,
  filter: BlueprintFilter
): boolean {
  if (filter === "standard") return blueprint.is_standard_issue;
  if (filter === "required") return !blueprint.is_standard_issue;
  return true;
}
