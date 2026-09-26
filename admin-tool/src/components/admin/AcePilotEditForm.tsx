/* admin-tool/src/components/admin/AcePilotEditForm.tsx */
"use client";

import { useEffect, useState } from "react";
import { useForm, useFieldArray, FieldErrors, FormProvider } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AcePilot, AcePilotCreate, MasterMobileSuit } from "@/types/admin";
import { Weapon } from "@/types/weapon";
import MasterMobileSuitSelect from "@/components/admin/MasterMobileSuitSelect";
import { useAdminWeapons } from "@/hooks/useAdminWeapons";
import {
  DEFAULT_WEAPON_SLOT_COUNT,
  FieldError,
  Input,
  Label,
  MobileSuitSpecSection,
  WeaponListSection,
  defaultWeapon,
  inputCls,
  masterToSpecValues,
  mergeWeaponSources,
  missingPartsToFormValues,
  mobileSuitSpecSchema,
  refineWeaponSlots,
  sectionTitle,
  tacticsToFormValues,
  weaponToFormValues,
} from "@/components/admin/MobileSuitSpecFields";

// ============================================================
// 定数
// ============================================================

const PERSONALITIES = ["AGGRESSIVE", "CAUTIOUS", "SNIPER"] as const;

// backend/app/core/skills.py の SKILL_MASTER_DATA と同期させること
const SKILL_OPTIONS = [
  { id: "flanking", name: "フランキング", maxLevel: 3 },
  { id: "accuracy_up", name: "命中率向上", maxLevel: 10 },
  { id: "evasion_up", name: "回避率向上", maxLevel: 10 },
  { id: "damage_up", name: "攻撃力向上", maxLevel: 10 },
  { id: "crit_rate_up", name: "クリティカル率向上", maxLevel: 10 },
] as const;

const STAT_FIELDS = [
  ["sht", "射撃精度 (SHT)"],
  ["mel", "格闘技巧 (MEL)"],
  ["intel", "直感 (INT)"],
  ["ref", "反応 (REF)"],
  ["tou", "耐久 (TOU)"],
  ["luk", "幸運 (LUK)"],
] as const;

// ============================================================
// Zod バリデーションスキーマ
// ============================================================

const statSchema = z.number({ message: "Must be a number" }).int().nonnegative("Must be ≥ 0");

export const acePilotSchema = z
  .object({
    id: z
      .string()
      .min(1, "ID is required")
      .regex(/^[a-z0-9_]+$/, "ID must be lowercase alphanumeric with underscores (snake_case)"),
    name: z.string().min(1, "Name is required"),
    pilot_name: z.string().min(1, "Pilot name is required"),
    description: z.string(),
    personality: z.enum(PERSONALITIES),
    bounty_exp: z.number({ message: "Must be a number" }).int().nonnegative("Must be ≥ 0"),
    bounty_credits: z.number({ message: "Must be a number" }).int().nonnegative("Must be ≥ 0"),
    stats: z.object({
      sht: statSchema,
      mel: statSchema,
      intel: statSchema,
      ref: statSchema,
      tou: statSchema,
      luk: statSchema,
    }),
    skills: z.array(
      z.object({
        id: z.string().min(1),
        level: z.number({ message: "Must be a number" }).int().nonnegative("Must be ≥ 0"),
      })
    ),
    mobile_suit: mobileSuitSpecSchema.superRefine(refineWeaponSlots),
  })
  .superRefine((data, ctx) => {
    const seen = new Set<string>();
    data.skills.forEach((skill, index) => {
      const def = SKILL_OPTIONS.find((s) => s.id === skill.id);
      if (seen.has(skill.id)) {
        ctx.addIssue({ code: "custom", message: "Duplicate skill", path: ["skills", index, "id"] });
      }
      seen.add(skill.id);
      if (def && skill.level > def.maxLevel) {
        ctx.addIssue({
          code: "custom",
          message: `Max level is ${def.maxLevel}`,
          path: ["skills", index, "level"],
        });
      }
    });
  });

export type AcePilotFormValues = z.infer<typeof acePilotSchema>;

// ============================================================
// 変換ヘルパー
// ============================================================

const defaultValues: AcePilotFormValues = {
  id: "",
  name: "",
  pilot_name: "",
  description: "",
  personality: "AGGRESSIVE",
  bounty_exp: 500,
  bounty_credits: 1000,
  stats: { sht: 10, mel: 10, intel: 10, ref: 10, tou: 10, luk: 10 },
  skills: [{ id: "flanking", level: 2 }],
  mobile_suit: {
    master_mobile_suit_id: null,
    name: "",
    max_hp: 1200,
    armor: 80,
    mobility: 2.0,
    sensor_range: 700,
    beam_resistance: 0.1,
    physical_resistance: 0.1,
    max_en: 1500,
    en_recovery: 150,
    tactics: { priority: "CLOSEST", range: "BALANCED" },
    missing_parts: [],
    weapon_slot_count: DEFAULT_WEAPON_SLOT_COUNT,
    weapons: [{ ...defaultWeapon }],
  },
};

function toFormValues(ace: AcePilot): AcePilotFormValues {
  const ms = ace.mobile_suit;
  return {
    id: ace.id,
    name: ace.name,
    pilot_name: ace.pilot_name,
    description: ace.description ?? "",
    personality: ace.personality,
    bounty_exp: ace.bounty_exp,
    bounty_credits: ace.bounty_credits,
    stats: { ...ace.stats },
    skills: Object.entries(ace.skills ?? {}).map(([id, level]) => ({ id, level })),
    mobile_suit: {
      master_mobile_suit_id: ms.master_mobile_suit_id ?? null,
      name: ms.name,
      max_hp: ms.max_hp,
      armor: ms.armor,
      mobility: ms.mobility,
      sensor_range: ms.sensor_range,
      beam_resistance: ms.beam_resistance,
      physical_resistance: ms.physical_resistance,
      max_en: ms.max_en,
      en_recovery: ms.en_recovery,
      tactics: tacticsToFormValues(ms.tactics),
      missing_parts: missingPartsToFormValues(ms.missing_parts),
      // 未設定の雛形はマッチング時と同じく装備数と既定値の大きい方を表示する
      weapon_slot_count: ms.weapon_slot_count ?? Math.max(ms.weapons.length, DEFAULT_WEAPON_SLOT_COUNT),
      weapons: ms.weapons.map(weaponToFormValues),
    },
  };
}

/**
 * フォーム値を API リクエストに変換する。
 * 武装の取り込み元は既存エースの武装と、機体マスター・武器マスターから取り込んだ武装。
 */
export function toAcePilotPayload(
  values: AcePilotFormValues,
  original: AcePilot | null,
  importedWeapons: Weapon[] = []
): AcePilotCreate {
  return {
    ...values,
    skills: Object.fromEntries(values.skills.map((s) => [s.id, s.level])),
    mobile_suit: {
      ...values.mobile_suit,
      weapons: mergeWeaponSources(values.mobile_suit.weapons, [
        ...(original?.mobile_suit.weapons ?? []),
        ...importedWeapons,
      ]),
    },
  };
}

// ============================================================
// UI 部品
// ============================================================

type Tab = "basic" | "mobile_suit" | "weapons" | "pilot";

const TABS: [Tab, string][] = [
  ["basic", "基本情報"],
  ["mobile_suit", "機体"],
  ["weapons", "武装"],
  ["pilot", "パイロット"],
];

/** 非表示タブのエラーを見落とさないよう、タブごとにエラー有無を判定する */
function tabHasError(tab: Tab, errors: FieldErrors<AcePilotFormValues>): boolean {
  switch (tab) {
    case "basic":
      return !!(errors.id || errors.name || errors.pilot_name || errors.description || errors.personality || errors.bounty_exp || errors.bounty_credits);
    case "mobile_suit":
      return Object.keys(errors.mobile_suit ?? {}).some((key) => key !== "weapons");
    case "weapons":
      return !!errors.mobile_suit?.weapons;
    case "pilot":
      return !!(errors.stats || errors.skills);
  }
}

// ============================================================
// コンポーネント
// ============================================================

interface AcePilotEditFormProps {
  /** 編集対象エース（null の場合は新規作成モード） */
  initialData: AcePilot | null;
  /** idフィールドを編集不可にする（既存エースの更新時） */
  lockId?: boolean;
  /** importedWeapons は機体マスター・武器マスターから取り込んだ武装。toAcePilotPayload に渡す。 */
  onSubmit: (values: AcePilotFormValues, importedWeapons: Weapon[]) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export default function AcePilotEditForm({
  initialData,
  lockId = false,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: AcePilotEditFormProps) {
  "use no memo";
  const [tab, setTab] = useState<Tab>("basic");
  // 取り込んだ武装は、取り込んだ時点の編集対象に紐付ける。
  // initialData が変わったら（別エースへの切替・保存後の再取得）空として扱い、次の保存に混ぜない。
  const [imported, setImported] = useState<{ source: AcePilot | null; weapons: Weapon[] }>({
    source: initialData,
    weapons: [],
  });
  const importedWeapons = imported.source === initialData ? imported.weapons : [];
  const methods = useForm<AcePilotFormValues>({
    resolver: zodResolver(acePilotSchema),
    defaultValues: initialData ? toFormValues(initialData) : defaultValues,
  });
  const {
    register,
    handleSubmit,
    control,
    reset,
    getValues,
    formState: { errors, isDirty },
  } = methods;

  const skillArray = useFieldArray({ control, name: "skills" });
  const { weapons: masterWeapons } = useAdminWeapons();

  useEffect(() => {
    reset(initialData ? toFormValues(initialData) : defaultValues);
  }, [initialData, reset]);

  function handleImportMaster(master: MasterMobileSuit) {
    const needsConfirm = initialData !== null || isDirty;
    if (
      needsConfirm &&
      !window.confirm(`機体スペックと武装を「${master.name}」の内容で上書きします。よろしいですか？`)
    ) {
      return;
    }
    // reset で書き換える。setValue では武装の useFieldArray が追従しないため。
    reset(
      {
        ...getValues(),
        mobile_suit: masterToSpecValues(
          master,
          getValues("mobile_suit"),
          new Set((masterWeapons ?? []).map((w) => w.id))
        ),
      },
      { keepDefaultValues: true }
    );
    setImported({ source: initialData, weapons: [...importedWeapons, ...master.specs.weapons] });
  }

  // バリデーションエラー時は、エラーを含む最初のタブへ切り替える
  function handleInvalid(invalidErrors: FieldErrors<AcePilotFormValues>) {
    const firstErrorTab = TABS.find(([key]) => tabHasError(key, invalidErrors));
    if (firstErrorTab) setTab(firstErrorTab[0]);
  }

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit((values) => onSubmit(values, importedWeapons), handleInvalid)}
        className="space-y-4 text-[#00ff41] font-mono"
      >
        {/* タブ */}
        <div className="flex border-b border-[#00ff41]/20">
          {TABS.map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`px-3 py-1.5 text-xs font-bold border-b-2 -mb-px transition-colors ${
                tab === key
                  ? "border-[#ffb000] text-[#ffb000]"
                  : "border-transparent text-[#00ff41]/60 hover:text-[#00ff41]"
              }`}
            >
              {label}
              {tabHasError(key, errors) && <span className="ml-1 text-red-400">!</span>}
            </button>
          ))}
        </div>

        {/* 基本情報 */}
        <div className={tab === "basic" ? "space-y-4" : "hidden"}>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>ID (snake_case)</Label>
              <Input {...register("id")} disabled={lockId} placeholder="ace_char_aznable" />
              <FieldError msg={errors.id?.message} />
            </div>
            <div>
              <Label>二つ名</Label>
              <Input {...register("name")} placeholder="赤い彗星" />
              <FieldError msg={errors.name?.message} />
            </div>
            <div>
              <Label>パイロット名</Label>
              <Input {...register("pilot_name")} placeholder="Char Aznable" />
              <FieldError msg={errors.pilot_name?.message} />
            </div>
            <div>
              <Label>性格</Label>
              <select {...register("personality")} className={inputCls}>
                {PERSONALITIES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
              <FieldError msg={errors.personality?.message} />
            </div>
            <div>
              <Label>賞金 EXP</Label>
              <Input type="number" {...register("bounty_exp", { valueAsNumber: true })} />
              <FieldError msg={errors.bounty_exp?.message} />
            </div>
            <div>
              <Label>賞金 Credits</Label>
              <Input type="number" {...register("bounty_credits", { valueAsNumber: true })} />
              <FieldError msg={errors.bounty_credits?.message} />
            </div>
            <div className="col-span-2">
              <Label>説明</Label>
              <textarea {...register("description")} rows={2} className={`${inputCls} resize-none`} />
              <FieldError msg={errors.description?.message} />
            </div>
          </div>
          <p className="text-xs text-[#00ff41]/40">
            ※ パイロット名はNPC管理画面のエース判定（名前一致）にも使われます
          </p>
        </div>

        {/* 機体 */}
        <div className={tab === "mobile_suit" ? "space-y-4" : "hidden"}>
          <div>
            <p className={sectionTitle}>機体マスターから取り込み</p>
            <MasterMobileSuitSelect buttonLabel="取り込み" onApply={handleImportMaster} />
            <p className="mt-1 text-xs text-[#00ff41]/40">
              ※ 機体名・スペック・欠損部位・武器スロット数・武装を上書きします。EN と戦術は機体マスターに無いため現在の値を残します。取り込んだ機体マスターを記録し、各項目にマスターの値を併記します
            </p>
          </div>
          <MobileSuitSpecSection namePlaceholder="High Mobility Zaku II (Red)" />
        </div>

        {/* 武装 */}
        <div className={tab === "weapons" ? "" : "hidden"}>
          <WeaponListSection
            idPrefix="ace"
            onImportWeapon={(weapon) =>
              setImported({ source: initialData, weapons: [...importedWeapons, weapon] })
            }
          />
        </div>

        {/* パイロット */}
        <div className={tab === "pilot" ? "space-y-4" : "hidden"}>
          <div>
            <p className={sectionTitle}>ステータス</p>
            <div className="grid grid-cols-3 gap-3">
              {STAT_FIELDS.map(([key, label]) => (
                <div key={key}>
                  <Label>{label}</Label>
                  <Input type="number" min={0} {...register(`stats.${key}`, { valueAsNumber: true })} />
                  <FieldError msg={errors.stats?.[key]?.message} />
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <p className={`${sectionTitle} flex-1`}>スキル</p>
              <button
                type="button"
                disabled={skillArray.fields.length >= SKILL_OPTIONS.length}
                onClick={() => {
                  const used = new Set(skillArray.fields.map((f) => f.id));
                  const next = SKILL_OPTIONS.find((s) => !used.has(s.id)) ?? SKILL_OPTIONS[0];
                  skillArray.append({ id: next.id, level: 1 });
                }}
                className="text-xs text-[#00ff41] border border-[#00ff41]/40 px-2 py-0.5 hover:border-[#00ff41] ml-4 disabled:opacity-40"
              >
                + 追加
              </button>
            </div>
            <div className="space-y-2">
              {skillArray.fields.map((field, index) => (
                <div key={field.id} className="grid grid-cols-[1fr_6rem_auto] gap-2 items-start">
                  <div>
                    <select {...register(`skills.${index}.id`)} className={inputCls}>
                      {SKILL_OPTIONS.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name} ({s.id}, Max Lv.{s.maxLevel})
                        </option>
                      ))}
                    </select>
                    <FieldError msg={errors.skills?.[index]?.id?.message} />
                  </div>
                  <div>
                    <Input type="number" min={0} {...register(`skills.${index}.level`, { valueAsNumber: true })} />
                    <FieldError msg={errors.skills?.[index]?.level?.message} />
                  </div>
                  <button
                    type="button"
                    onClick={() => skillArray.remove(index)}
                    className="text-xs text-red-400 hover:text-red-300 py-1"
                  >
                    削除
                  </button>
                </div>
              ))}
              {skillArray.fields.length === 0 && <p className="text-xs text-[#00ff41]/40">スキルなし</p>}
            </div>
            <p className="mt-2 text-xs text-[#00ff41]/40">
              ※ 現在NPC戦闘で参照されるのは flanking のみです
            </p>
          </div>
        </div>

        {/* ボタン */}
        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex-1 bg-[#00ff41]/10 border border-[#00ff41] text-[#00ff41] py-2 text-sm font-bold hover:bg-[#00ff41]/20 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? "保存中..." : "保存"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 bg-transparent border border-[#00ff41]/30 text-[#00ff41]/60 py-2 text-sm hover:border-[#00ff41]/60 transition-colors"
          >
            キャンセル
          </button>
        </div>
      </form>
    </FormProvider>
  );
}
