"use client";

import { UseFormRegisterReturn } from "react-hook-form";
import { z } from "zod";
import { MasterBlueprintSettings, TechRequirement } from "@/types/admin";
import { BLUEPRINT_FILTER_LABELS, BlueprintFilter } from "@/lib/blueprint";
import { maxLevelOf, newTechRequirement, techRequirementsSchema } from "@/lib/technology";
import { useAdminTechnologies } from "@/hooks/useAdminTechnologies";

// 換金額の空欄は null で送る。backend は null の項目を変更しない（新規作成時は初期値にする）。
export const blueprintFormSchema = z.object({
  is_standard_issue: z.boolean(),
  duplicate_credit_value: z
    .number({ message: "Must be a number" })
    .int("Must be an integer")
    .nonnegative("Must be ≥ 0")
    .nullable(),
  tech_requirements: techRequirementsSchema,
});

export type BlueprintFormValues = z.infer<typeof blueprintFormSchema>;

export function toBlueprintFormValues(
  blueprint: MasterBlueprintSettings | null
): BlueprintFormValues {
  if (!blueprint) return { is_standard_issue: true, duplicate_credit_value: null, tech_requirements: [] };
  return {
    ...blueprint,
    tech_requirements: blueprint.tech_requirements.map((r) => ({ ...r })),
  };
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
  /** `blueprint.tech_requirements` の値と更新関数（`Controller` の field） */
  techRequirements: TechRequirement[];
  onTechRequirementsChange: (next: TechRequirement[]) => void;
  techRequirementsError?: string;
}

export default function BlueprintSettingsFields({
  standardIssueField,
  creditValueField,
  creditValueError,
  defaultCreditValue,
  techRequirements,
  onTechRequirementsChange,
  techRequirementsError,
}: BlueprintSettingsFieldsProps) {
  const placeholder =
    defaultCreditValue === null ? "空欄=変更しない" : `空欄=初期値 (${defaultCreditValue.toLocaleString()} C)`;

  return (
    <div className="space-y-3">
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
      <TechRequirementRows
        value={techRequirements}
        onChange={onTechRequirementsChange}
        error={techRequirementsError}
      />
    </div>
  );
}

const selectCls =
  "bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41]";

/** 購入に必要な技術Lvの行（技術の選択 ＋ Lv）の追加・削除 */
function TechRequirementRows({
  value,
  onChange,
  error,
}: {
  value: TechRequirement[];
  onChange: (next: TechRequirement[]) => void;
  error?: string;
}) {
  const { technologies, isLoading, isError } = useAdminTechnologies();
  const techList = technologies ?? [];
  const nextRequirement = newTechRequirement(techList, value);

  function update(index: number, patch: Partial<TechRequirement>) {
    onChange(value.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }

  return (
    <div>
      <label className="block text-xs text-[#ffb000]/80 mb-0.5">必要な技術Lv</label>
      {value.length === 0 && <p className="text-xs text-[#00ff41]/40">なし（設計図だけで購入できる）</p>}
      <ul className="space-y-1">
        {value.map((requirement, index) => {
          const tech = techList.find((t) => t.id === requirement.tech_id);
          const maxLevel = tech ? maxLevelOf(tech) : requirement.required_lv;
          return (
            <li key={index} className="flex items-center gap-2">
              <select
                aria-label="技術"
                value={requirement.tech_id}
                onChange={(e) => update(index, { tech_id: e.target.value, required_lv: 1 })}
                className={`flex-1 ${selectCls}`}
              >
                {!tech && <option value={requirement.tech_id}>{requirement.tech_id}</option>}
                {techList.map((t) => (
                  <option
                    key={t.id}
                    value={t.id}
                    disabled={t.id !== requirement.tech_id && value.some((r) => r.tech_id === t.id)}
                  >
                    {t.name} ({t.id})
                  </option>
                ))}
              </select>
              <select
                aria-label="必要Lv"
                value={requirement.required_lv}
                onChange={(e) => update(index, { required_lv: Number(e.target.value) })}
                className={selectCls}
              >
                {Array.from({ length: Math.max(maxLevel, requirement.required_lv) }, (_, i) => i + 1).map(
                  (lv) => (
                    <option key={lv} value={lv}>
                      Lv{lv}
                    </option>
                  )
                )}
              </select>
              <button
                type="button"
                onClick={() => onChange(value.filter((_, i) => i !== index))}
                className="text-xs text-red-400 border border-red-500/40 px-2 py-0.5 hover:border-red-500"
              >
                削除
              </button>
            </li>
          );
        })}
      </ul>
      <button
        type="button"
        disabled={!nextRequirement}
        onClick={() => nextRequirement && onChange([...value, nextRequirement])}
        className="mt-1 text-xs text-[#00ff41] border border-[#00ff41]/40 px-2 py-0.5 hover:border-[#00ff41] disabled:opacity-40 disabled:cursor-not-allowed"
      >
        + 技術Lvを追加
      </button>
      {isLoading && <span className="ml-2 text-xs text-[#00ff41]/40">技術マスターを読み込み中...</span>}
      {isError && <span className="ml-2 text-xs text-red-400">技術マスターを取得できません</span>}
      {error && <p className="mt-0.5 text-xs text-red-400">{error}</p>}
      <p className="mt-0.5 text-xs text-[#00ff41]/40">
        標準配備なら判定しない。技術Lvは機体の beam_generator_lv（装備できるビーム武器のLv）とは別物
      </p>
    </div>
  );
}

export function BlueprintBadge({
  blueprint,
}: {
  blueprint: Pick<MasterBlueprintSettings, "is_standard_issue">;
}) {
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
