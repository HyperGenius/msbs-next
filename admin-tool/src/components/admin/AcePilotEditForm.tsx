/* admin-tool/src/components/admin/AcePilotEditForm.tsx */
"use client";

import { useEffect, useState } from "react";
import { useForm, useFieldArray, Controller, FieldErrors } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AcePilot, AcePilotCreate } from "@/types/admin";
import { weaponSchema } from "@/components/admin/MobileSuitEditForm";

// ============================================================
// 定数
// ============================================================

const PERSONALITIES = ["AGGRESSIVE", "CAUTIOUS", "SNIPER"] as const;
const TACTICS_PRIORITIES = ["CLOSEST", "WEAKEST", "RANDOM", "STRONGEST", "THREAT"] as const;
const TACTICS_RANGES = ["MELEE", "RANGED", "BALANCED", "FLEE"] as const;
const PART_NAMES = ["HEAD", "TORSO", "RIGHT_ARM", "LEFT_ARM", "RIGHT_LEG", "LEFT_LEG"] as const;

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
    mobile_suit: z.object({
      name: z.string().min(1, "Mobile suit name is required"),
      max_hp: z.number({ message: "Must be a number" }).int().positive("Must be > 0"),
      armor: z.number({ message: "Must be a number" }).int().nonnegative(),
      mobility: z.number({ message: "Must be a number" }).positive("Must be > 0"),
      sensor_range: z.number({ message: "Must be a number" }).positive(),
      beam_resistance: z.number({ message: "Must be a number" }).min(0).max(1),
      physical_resistance: z.number({ message: "Must be a number" }).min(0).max(1),
      max_en: z.number({ message: "Must be a number" }).int().nonnegative(),
      en_recovery: z.number({ message: "Must be a number" }).int().nonnegative(),
      tactics: z.object({
        priority: z.enum(TACTICS_PRIORITIES),
        range: z.enum(TACTICS_RANGES),
      }),
      missing_parts: z.array(z.enum(PART_NAMES)),
      weapons: z.array(weaponSchema).min(1, "At least one weapon is required"),
    }),
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
type WeaponFormValues = AcePilotFormValues["mobile_suit"]["weapons"][number];

// ============================================================
// 変換ヘルパー
// ============================================================

const defaultWeapon: WeaponFormValues = {
  id: "",
  name: "",
  power: 150,
  range: 400,
  accuracy: 80,
  type: "PHYSICAL",
  optimal_range: 300,
  decay_rate: 0.05,
  is_melee: false,
  en_cost: 0,
  cool_down_turn: 0,
  required_beam_generator_lv: 0,
};

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
      name: ms.name,
      max_hp: ms.max_hp,
      armor: ms.armor,
      mobility: ms.mobility,
      sensor_range: ms.sensor_range,
      beam_resistance: ms.beam_resistance,
      physical_resistance: ms.physical_resistance,
      max_en: ms.max_en,
      en_recovery: ms.en_recovery,
      tactics: {
        priority: (ms.tactics?.priority ?? "CLOSEST") as AcePilotFormValues["mobile_suit"]["tactics"]["priority"],
        range: (ms.tactics?.range ?? "BALANCED") as AcePilotFormValues["mobile_suit"]["tactics"]["range"],
      },
      missing_parts: (ms.missing_parts ?? []) as AcePilotFormValues["mobile_suit"]["missing_parts"],
      weapons: ms.weapons.map((w) => ({
        id: w.id,
        name: w.name,
        power: w.power,
        range: w.range,
        accuracy: w.accuracy,
        type: (w.type ?? "PHYSICAL") as "BEAM" | "PHYSICAL",
        optimal_range: w.optimal_range ?? 300,
        decay_rate: w.decay_rate ?? 0.05,
        is_melee: w.is_melee ?? false,
        max_ammo: w.max_ammo ?? null,
        en_cost: w.en_cost ?? 0,
        cool_down_turn: w.cool_down_turn ?? 0,
        required_beam_generator_lv: w.required_beam_generator_lv ?? 0,
      })),
    },
  };
}

/**
 * フォーム値を API リクエストに変換する。
 * フォームで扱わない武器項目（weapon_type / cooldown_sec / fire_arc_deg / aim_distribution 等）は
 * 同じ武器IDの既存値を引き継ぎ、編集によって既定値へ巻き戻らないようにする。
 */
export function toAcePilotPayload(values: AcePilotFormValues, original: AcePilot | null): AcePilotCreate {
  const originalWeapons = new Map((original?.mobile_suit.weapons ?? []).map((w) => [w.id, w]));
  return {
    ...values,
    skills: Object.fromEntries(values.skills.map((s) => [s.id, s.level])),
    mobile_suit: {
      ...values.mobile_suit,
      weapons: values.mobile_suit.weapons.map((w) => ({ ...originalWeapons.get(w.id), ...w })),
    },
  };
}

// ============================================================
// UI 部品
// ============================================================

function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return <p className="mt-0.5 text-xs text-red-400">{msg}</p>;
}

function Label({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="block text-xs text-[#ffb000]/80 mb-0.5">
      {children}
    </label>
  );
}

function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41] disabled:opacity-50 ${className ?? ""}`}
    />
  );
}

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
  onSubmit: (values: AcePilotFormValues) => Promise<void>;
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
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<AcePilotFormValues>({
    resolver: zodResolver(acePilotSchema),
    defaultValues: initialData ? toFormValues(initialData) : defaultValues,
  });

  const weaponArray = useFieldArray({ control, name: "mobile_suit.weapons" });
  const skillArray = useFieldArray({ control, name: "skills" });

  useEffect(() => {
    reset(initialData ? toFormValues(initialData) : defaultValues);
  }, [initialData, reset]);

  // バリデーションエラー時は、エラーを含む最初のタブへ切り替える
  function handleInvalid(invalidErrors: FieldErrors<AcePilotFormValues>) {
    const firstErrorTab = TABS.find(([key]) => tabHasError(key, invalidErrors));
    if (firstErrorTab) setTab(firstErrorTab[0]);
  }

  const inputCls =
    "w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41]";
  const sectionTitle =
    "text-xs font-bold text-[#ffb000] uppercase tracking-wider mb-2 border-b border-[#ffb000]/20 pb-1";
  const msErrors = errors.mobile_suit;

  return (
    <form onSubmit={handleSubmit(onSubmit, handleInvalid)} className="space-y-4 text-[#00ff41] font-mono">
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
          <p className={sectionTitle}>スペック</p>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-3">
              <Label>機体名</Label>
              <Input {...register("mobile_suit.name")} placeholder="High Mobility Zaku II (Red)" />
              <FieldError msg={msErrors?.name?.message} />
            </div>
            {(
              [
                ["mobile_suit.max_hp", "最大 HP", "1", msErrors?.max_hp?.message],
                ["mobile_suit.armor", "装甲", "1", msErrors?.armor?.message],
                ["mobile_suit.mobility", "機動性", "0.01", msErrors?.mobility?.message],
                ["mobile_suit.sensor_range", "索敵範囲", "1", msErrors?.sensor_range?.message],
                ["mobile_suit.beam_resistance", "ビーム耐性 (0-1)", "0.01", msErrors?.beam_resistance?.message],
                ["mobile_suit.physical_resistance", "実弾耐性 (0-1)", "0.01", msErrors?.physical_resistance?.message],
                ["mobile_suit.max_en", "最大 EN", "1", msErrors?.max_en?.message],
                ["mobile_suit.en_recovery", "EN 回復量", "1", msErrors?.en_recovery?.message],
              ] as const
            ).map(([name, label, step, error]) => (
              <div key={name}>
                <Label>{label}</Label>
                <Input type="number" step={step} {...register(name, { valueAsNumber: true })} />
                <FieldError msg={error} />
              </div>
            ))}
          </div>
        </div>

        <div>
          <p className={sectionTitle}>戦術</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>ターゲット優先度</Label>
              <select {...register("mobile_suit.tactics.priority")} className={inputCls}>
                {TACTICS_PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>交戦距離</Label>
              <select {...register("mobile_suit.tactics.range")} className={inputCls}>
                {TACTICS_RANGES.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div>
          <p className={sectionTitle}>欠損部位</p>
          <Controller
            control={control}
            name="mobile_suit.missing_parts"
            render={({ field }) => (
              <div className="grid grid-cols-3 gap-2">
                {PART_NAMES.map((part) => (
                  <label key={part} className="flex items-center gap-2 text-xs text-[#00ff41]/80">
                    <input
                      type="checkbox"
                      className="accent-[#00ff41]"
                      checked={field.value.includes(part)}
                      onChange={(e) =>
                        field.onChange(
                          e.target.checked ? [...field.value, part] : field.value.filter((p) => p !== part)
                        )
                      }
                    />
                    {part}
                  </label>
                ))}
              </div>
            )}
          />
        </div>
      </div>

      {/* 武装 */}
      <div className={tab === "weapons" ? "" : "hidden"}>
        <div className="flex items-center justify-between mb-2">
          <p className={`${sectionTitle} flex-1`}>武装</p>
          <button
            type="button"
            onClick={() => weaponArray.append({ ...defaultWeapon })}
            className="text-xs text-[#00ff41] border border-[#00ff41]/40 px-2 py-0.5 hover:border-[#00ff41] ml-4"
          >
            + 追加
          </button>
        </div>
        {msErrors?.weapons?.message && <p className="text-xs text-red-400 mb-2">{msErrors.weapons.message}</p>}
        <div className="space-y-4">
          {weaponArray.fields.map((field, index) => {
            const wErrors = msErrors?.weapons?.[index];
            return (
              <div key={field.id} className="border border-[#00ff41]/20 p-3 bg-[#080808]">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs text-[#ffb000]/60">武器 #{index + 1}</span>
                  {weaponArray.fields.length > 1 && (
                    <button
                      type="button"
                      onClick={() => weaponArray.remove(index)}
                      className="text-xs text-red-400 hover:text-red-300"
                    >
                      削除
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <Label>ID (snake_case)</Label>
                    <Input {...register(`mobile_suit.weapons.${index}.id`)} placeholder="ace_beam_rifle" />
                    <FieldError msg={wErrors?.id?.message} />
                  </div>
                  <div className="col-span-2">
                    <Label>名前</Label>
                    <Input {...register(`mobile_suit.weapons.${index}.name`)} placeholder="Beam Rifle" />
                    <FieldError msg={wErrors?.name?.message} />
                  </div>
                  <div>
                    <Label>威力</Label>
                    <Input type="number" {...register(`mobile_suit.weapons.${index}.power`, { valueAsNumber: true })} />
                    <FieldError msg={wErrors?.power?.message} />
                  </div>
                  <div>
                    <Label>射程</Label>
                    <Input type="number" {...register(`mobile_suit.weapons.${index}.range`, { valueAsNumber: true })} />
                    <FieldError msg={wErrors?.range?.message} />
                  </div>
                  <div>
                    <Label>命中率 (%)</Label>
                    <Input
                      type="number"
                      {...register(`mobile_suit.weapons.${index}.accuracy`, { valueAsNumber: true })}
                    />
                    <FieldError msg={wErrors?.accuracy?.message} />
                  </div>
                  <div>
                    <Label>種別</Label>
                    <select {...register(`mobile_suit.weapons.${index}.type`)} className={inputCls}>
                      <option value="PHYSICAL">PHYSICAL</option>
                      <option value="BEAM">BEAM</option>
                    </select>
                  </div>
                  <div>
                    <Label>最適射程</Label>
                    <Input
                      type="number"
                      step="0.1"
                      {...register(`mobile_suit.weapons.${index}.optimal_range`, { valueAsNumber: true })}
                    />
                  </div>
                  <div>
                    <Label>減衰係数</Label>
                    <Input
                      type="number"
                      step="0.01"
                      {...register(`mobile_suit.weapons.${index}.decay_rate`, { valueAsNumber: true })}
                    />
                  </div>
                  <div>
                    <Label>消費 EN</Label>
                    <Input
                      type="number"
                      min={0}
                      {...register(`mobile_suit.weapons.${index}.en_cost`, { valueAsNumber: true })}
                    />
                    <FieldError msg={wErrors?.en_cost?.message} />
                  </div>
                  <div className="flex items-center gap-2 mt-3">
                    <Controller
                      control={control}
                      name={`mobile_suit.weapons.${index}.is_melee`}
                      render={({ field: f }) => (
                        <input
                          type="checkbox"
                          id={`ace_is_melee_${index}`}
                          checked={f.value}
                          onChange={f.onChange}
                          className="accent-[#00ff41]"
                        />
                      )}
                    />
                    <label htmlFor={`ace_is_melee_${index}`} className="text-xs text-[#00ff41]/80">
                      近接武器
                    </label>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
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
  );
}
