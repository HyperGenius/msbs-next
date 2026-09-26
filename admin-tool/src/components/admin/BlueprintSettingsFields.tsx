"use client";

import { UseFormRegisterReturn } from "react-hook-form";
import { z } from "zod";
import { MasterBlueprintSettings } from "@/types/admin";
import { BLUEPRINT_FILTER_LABELS, BlueprintFilter } from "@/lib/blueprint";

// 換金額の空欄は null で送る。backend は null の項目を変更しない（新規作成時は初期値にする）。
export const blueprintFormSchema = z.object({
  is_standard_issue: z.boolean(),
  duplicate_credit_value: z
    .number({ message: "Must be a number" })
    .int("Must be an integer")
    .nonnegative("Must be ≥ 0")
    .nullable(),
});

export type BlueprintFormValues = z.infer<typeof blueprintFormSchema>;

export function toBlueprintFormValues(
  blueprint: MasterBlueprintSettings | null
): BlueprintFormValues {
  if (!blueprint) return { is_standard_issue: true, duplicate_credit_value: null };
  return { ...blueprint };
}

/** 数値入力の空欄を null として読むための `register` オプション。 */
export const nullableNumberOptions = {
  setValueAs: (v: unknown) => (v === "" || v === null ? null : Number(v)),
};

interface BlueprintSettingsFieldsProps {
  /** `register("blueprint.is_standard_issue")` の戻り値 */
  standardIssueField: UseFormRegisterReturn;
  /** `register("blueprint.duplicate_credit_value", nullableNumberOptions)` の戻り値 */
  creditValueField: UseFormRegisterReturn;
  creditValueError?: string;
  /** 換金額を空欄で保存したときの値。新規作成なら初期値、編集なら null（変更しない） */
  defaultCreditValue: number | null;
}

export default function BlueprintSettingsFields({
  standardIssueField,
  creditValueField,
  creditValueError,
  defaultCreditValue,
}: BlueprintSettingsFieldsProps) {
  const placeholder =
    defaultCreditValue === null ? "空欄=変更しない" : `空欄=初期値 (${defaultCreditValue.toLocaleString()} C)`;

  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="flex items-center gap-2 mt-3">
        <input
          type="checkbox"
          id="blueprint_is_standard_issue"
          {...standardIssueField}
          className="accent-[#00ff41]"
        />
        <label htmlFor="blueprint_is_standard_issue" className="text-xs text-[#00ff41]/80">
          標準配備（設計図なしで購入できる）
        </label>
      </div>
      <div>
        <label className="block text-xs text-[#ffb000]/80 mb-0.5">重複時の換金額 (C)</label>
        <input
          type="number"
          min={0}
          placeholder={placeholder}
          {...creditValueField}
          className="w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41]"
        />
        {creditValueError && <p className="mt-0.5 text-xs text-red-400">{creditValueError}</p>}
        <p className="mt-0.5 text-xs text-[#00ff41]/40">価格を変えても換金額は変わりません</p>
      </div>
    </div>
  );
}

export function BlueprintBadge({ blueprint }: { blueprint: MasterBlueprintSettings }) {
  return blueprint.is_standard_issue ? (
    <span className="px-2 py-0.5 text-xs border border-[#00ff41]/30 text-[#00ff41]/70">標準配備</span>
  ) : (
    <span className="px-2 py-0.5 text-xs font-bold border border-[#ffb000]/50 text-[#ffb000] bg-[#ffb000]/10">
      要設計図
    </span>
  );
}

export function BlueprintFilterSelect({
  value,
  onChange,
}: {
  value: BlueprintFilter;
  onChange: (value: BlueprintFilter) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as BlueprintFilter)}
      aria-label="設計図で絞り込む"
      className="bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-3 py-2 text-sm font-mono focus:outline-none focus:border-[#00ff41]"
    >
      {(Object.keys(BLUEPRINT_FILTER_LABELS) as BlueprintFilter[]).map((key) => (
        <option key={key} value={key}>
          {BLUEPRINT_FILTER_LABELS[key]}
        </option>
      ))}
    </select>
  );
}
