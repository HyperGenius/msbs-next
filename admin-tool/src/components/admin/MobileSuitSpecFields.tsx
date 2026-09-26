/* admin-tool/src/components/admin/MobileSuitSpecFields.tsx */
"use client";

import { Controller, useFieldArray, useFormContext } from "react-hook-form";
import { z } from "zod";
import { MasterMobileSuit, NpcMobileSuit } from "@/types/admin";
import { Tactics, Weapon } from "@/types/weapon";
import { weaponSchema } from "@/components/admin/MobileSuitEditForm";

// ============================================================
// 定数
// ============================================================

export const TACTICS_PRIORITIES = ["CLOSEST", "WEAKEST", "RANDOM", "STRONGEST", "THREAT"] as const;
export const TACTICS_RANGES = ["MELEE", "RANGED", "BALANCED", "FLEE"] as const;
export const PART_NAMES = ["HEAD", "TORSO", "RIGHT_ARM", "LEFT_ARM", "RIGHT_LEG", "LEFT_LEG"] as const;

// ============================================================
// Zod バリデーションスキーマ
// ============================================================

/** エース機・NPC機に共通する機体スペック */
export const mobileSuitSpecSchema = z.object({
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
});

export type MobileSuitSpecFormValues = z.infer<typeof mobileSuitSpecSchema>;
export type WeaponFormValues = MobileSuitSpecFormValues["weapons"][number];

/** 共通セクションを載せるフォームの形。機体スペックは mobile_suit 配下に置く。 */
type SpecFormHost = { mobile_suit: MobileSuitSpecFormValues };

// ============================================================
// 変換ヘルパー
// ============================================================

export const defaultWeapon: WeaponFormValues = {
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

export function weaponToFormValues(w: Weapon): WeaponFormValues {
  return {
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
  };
}

export function tacticsToFormValues(tactics: Partial<Tactics> | undefined): MobileSuitSpecFormValues["tactics"] {
  const priority = TACTICS_PRIORITIES.find((p) => p === tactics?.priority) ?? "CLOSEST";
  const range = TACTICS_RANGES.find((r) => r === tactics?.range) ?? "BALANCED";
  return { priority, range };
}

export function missingPartsToFormValues(parts: string[] | undefined): MobileSuitSpecFormValues["missing_parts"] {
  return PART_NAMES.filter((p) => parts?.includes(p));
}

/**
 * フォームの武装を API に送る Weapon に変換する。
 * フォームで扱わない項目（weapon_type / cooldown_sec / fire_arc_deg / aim_distribution 等）は
 * 同じ武器IDの取り込み元から引き継ぐ。編集によって既定値へ巻き戻さないため。
 * sources に同じIDが複数あるときは後ろの要素を使う。
 */
export function mergeWeaponSources(weapons: WeaponFormValues[], sources: Weapon[]): Weapon[] {
  const byId = new Map(sources.map((w) => [w.id, w]));
  return weapons.map((w) => ({ ...byId.get(w.id), ...w }));
}

/**
 * 機体マスターのスペックをフォーム値に変換する。
 * 機体マスターに無い項目（EN・戦術）は current の値を残す。
 */
export function masterToSpecValues(
  master: MasterMobileSuit,
  current: MobileSuitSpecFormValues
): MobileSuitSpecFormValues {
  const specs = master.specs;
  return {
    ...current,
    name: master.name,
    max_hp: specs.max_hp,
    armor: specs.armor,
    mobility: specs.mobility,
    sensor_range: specs.sensor_range,
    beam_resistance: specs.beam_resistance,
    physical_resistance: specs.physical_resistance,
    missing_parts: missingPartsToFormValues(specs.missing_parts),
    weapons: specs.weapons.map(weaponToFormValues),
  };
}

export function npcMobileSuitToSpecValues(ms: NpcMobileSuit): MobileSuitSpecFormValues {
  return {
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
    weapons: ms.weapons.map(weaponToFormValues),
  };
}

// ============================================================
// UI 部品
// ============================================================

export const inputCls =
  "w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41]";
export const sectionTitle =
  "text-xs font-bold text-[#ffb000] uppercase tracking-wider mb-2 border-b border-[#ffb000]/20 pb-1";

export function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return <p className="mt-0.5 text-xs text-red-400">{msg}</p>;
}

export function Label({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="block text-xs text-[#ffb000]/80 mb-0.5">
      {children}
    </label>
  );
}

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputCls} disabled:opacity-50 ${className ?? ""}`} />;
}

// ============================================================
// フォームセクション（FormProvider 配下で使う）
// ============================================================

/** 機体スペック・戦術・欠損部位の入力欄 */
export function MobileSuitSpecSection({ namePlaceholder }: { namePlaceholder?: string }) {
  "use no memo";
  const {
    register,
    control,
    formState: { errors },
  } = useFormContext<SpecFormHost>();
  const msErrors = errors.mobile_suit;

  return (
    <>
      <div>
        <p className={sectionTitle}>スペック</p>
        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-3">
            <Label>機体名</Label>
            <Input {...register("mobile_suit.name")} placeholder={namePlaceholder} />
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
    </>
  );
}

/** 武装リストの入力欄。idPrefix は同一ページ内でチェックボックスの id を重複させないために使う。 */
export function WeaponListSection({ idPrefix }: { idPrefix: string }) {
  "use no memo";
  const {
    register,
    control,
    formState: { errors },
  } = useFormContext<SpecFormHost>();
  const weaponArray = useFieldArray({ control, name: "mobile_suit.weapons" });
  const weaponErrors = errors.mobile_suit?.weapons;

  return (
    <>
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
      {weaponErrors?.message && <p className="text-xs text-red-400 mb-2">{weaponErrors.message}</p>}
      <div className="space-y-4">
        {weaponArray.fields.map((field, index) => {
          const wErrors = weaponErrors?.[index];
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
                  <Input {...register(`mobile_suit.weapons.${index}.id`)} placeholder="beam_rifle" />
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
                        id={`${idPrefix}_is_melee_${index}`}
                        checked={f.value}
                        onChange={f.onChange}
                        className="accent-[#00ff41]"
                      />
                    )}
                  />
                  <label htmlFor={`${idPrefix}_is_melee_${index}`} className="text-xs text-[#00ff41]/80">
                    近接武器
                  </label>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
