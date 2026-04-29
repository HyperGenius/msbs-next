/* frontend/src/components/admin/MobileSuitEditForm.tsx */
"use client";

import { useEffect } from "react";
import { useForm, useFieldArray, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { MasterMobileSuit } from "@/types/battle";

// ============================================================
// Zod バリデーションスキーマ
// ============================================================

export const weaponSchema = z.object({
  id: z.string().min(1, "Weapon ID is required").regex(/^[a-z0-9_]+$/, "Weapon ID must be snake_case alphanumeric"),
  name: z.string().min(1, "Weapon name is required"),
  power: z.number({ invalid_type_error: "Must be a number" }).int().positive("Must be > 0"),
  range: z.number({ invalid_type_error: "Must be a number" }).positive("Must be > 0"),
  accuracy: z.number({ invalid_type_error: "Must be a number" }).min(0).max(100, "Must be 0-100"),
  type: z.enum(["BEAM", "PHYSICAL"]),
  optimal_range: z.number({ invalid_type_error: "Must be a number" }).nonnegative(),
  decay_rate: z.number({ invalid_type_error: "Must be a number" }).nonnegative(),
  is_melee: z.boolean(),
  max_ammo: z.number().int().nonnegative().nullable().optional(),
  en_cost: z.number().int().nonnegative().optional(),
  cool_down_turn: z.number().int().nonnegative().optional(),
});

export const masterMobileSuitSchema = z.object({
  id: z
    .string()
    .min(1, "ID is required")
    .regex(/^[a-z0-9_]+$/, "ID must be lowercase alphanumeric with underscores (snake_case)"),
  name: z.string().min(1, "Name is required"),
  price: z.number({ invalid_type_error: "Must be a number" }).int().nonnegative("Must be ≥ 0"),
  faction: z.string(),
  description: z.string(),
  specs: z.object({
    max_hp: z.number({ invalid_type_error: "Must be a number" }).int().positive("Must be > 0"),
    armor: z.number({ invalid_type_error: "Must be a number" }).int().nonnegative(),
    mobility: z.number({ invalid_type_error: "Must be a number" }).positive("Must be > 0"),
    sensor_range: z.number({ invalid_type_error: "Must be a number" }).positive(),
    beam_resistance: z.number({ invalid_type_error: "Must be a number" }).min(0).max(1),
    physical_resistance: z.number({ invalid_type_error: "Must be a number" }).min(0).max(1),
    melee_aptitude: z.number({ invalid_type_error: "Must be a number" }).positive(),
    shooting_aptitude: z.number({ invalid_type_error: "Must be a number" }).positive(),
    accuracy_bonus: z.number({ invalid_type_error: "Must be a number" }),
    evasion_bonus: z.number({ invalid_type_error: "Must be a number" }),
    acceleration_bonus: z.number({ invalid_type_error: "Must be a number" }).positive(),
    turning_bonus: z.number({ invalid_type_error: "Must be a number" }).positive(),
    weapons: z.array(weaponSchema).min(1, "At least one weapon is required"),
  }),
});

export type MobileSuitFormValues = z.infer<typeof masterMobileSuitSchema>;

// ============================================================
// コンポーネント
// ============================================================

interface MobileSuitEditFormProps {
  /** 編集対象機体（null の場合は新規作成モード） */
  initialData: MasterMobileSuit | null;
  /** idフィールドを編集不可にする（既存機体の更新時） */
  lockId?: boolean;
  onSubmit: (values: MobileSuitFormValues) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

const defaultWeapon: MobileSuitFormValues["specs"]["weapons"][0] = {
  id: "",
  name: "",
  power: 100,
  range: 400,
  accuracy: 60,
  type: "PHYSICAL",
  optimal_range: 300,
  decay_rate: 0.08,
  is_melee: false,
  en_cost: 0,
  cool_down_turn: 0,
};

const defaultValues: MobileSuitFormValues = {
  id: "",
  name: "",
  price: 500,
  faction: "",
  description: "",
  specs: {
    max_hp: 800,
    armor: 50,
    mobility: 1.0,
    sensor_range: 500,
    beam_resistance: 0,
    physical_resistance: 0,
    melee_aptitude: 1.0,
    shooting_aptitude: 1.0,
    accuracy_bonus: 0,
    evasion_bonus: 0,
    acceleration_bonus: 1.0,
    turning_bonus: 1.0,
    weapons: [{ ...defaultWeapon }],
  },
};

function toFormValues(ms: MasterMobileSuit): MobileSuitFormValues {
  return {
    id: ms.id,
    name: ms.name,
    price: ms.price,
    faction: ms.faction ?? "",
    description: ms.description,
    specs: {
      max_hp: ms.specs.max_hp,
      armor: ms.specs.armor,
      mobility: ms.specs.mobility,
      sensor_range: ms.specs.sensor_range ?? 500,
      beam_resistance: ms.specs.beam_resistance ?? 0,
      physical_resistance: ms.specs.physical_resistance ?? 0,
      melee_aptitude: ms.specs.melee_aptitude ?? 1.0,
      shooting_aptitude: ms.specs.shooting_aptitude ?? 1.0,
      accuracy_bonus: ms.specs.accuracy_bonus ?? 0,
      evasion_bonus: ms.specs.evasion_bonus ?? 0,
      acceleration_bonus: ms.specs.acceleration_bonus ?? 1.0,
      turning_bonus: ms.specs.turning_bonus ?? 1.0,
      weapons: ms.specs.weapons.map((w) => ({
        id: w.id,
        name: w.name,
        power: w.power,
        range: w.range,
        accuracy: w.accuracy,
        type: (w.type ?? "PHYSICAL") as "BEAM" | "PHYSICAL",
        optimal_range: w.optimal_range ?? 300,
        decay_rate: w.decay_rate ?? 0.08,
        is_melee: w.is_melee ?? false,
        max_ammo: w.max_ammo ?? null,
        en_cost: w.en_cost ?? 0,
        cool_down_turn: w.cool_down_turn ?? 0,
      })),
    },
  };
}

function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return <p className="mt-0.5 text-xs text-red-400">{msg}</p>;
}

function Label({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs text-[#ffb000]/80 mb-0.5">{children}</label>;
}

function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41] disabled:opacity-50 ${className ?? ""}`}
    />
  );
}

export default function MobileSuitEditForm({
  initialData,
  lockId = false,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: MobileSuitEditFormProps) {
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<MobileSuitFormValues>({
    resolver: zodResolver(masterMobileSuitSchema),
    defaultValues: initialData ? toFormValues(initialData) : defaultValues,
  });

  const { fields, append, remove } = useFieldArray({ control, name: "specs.weapons" });

  useEffect(() => {
    reset(initialData ? toFormValues(initialData) : defaultValues);
  }, [initialData, reset]);

  const inputCls = "w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41]";
  const sectionTitle = "text-xs font-bold text-[#ffb000] uppercase tracking-wider mb-2 border-b border-[#ffb000]/20 pb-1";

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-4 text-[#00ff41] font-mono"
    >
      {/* 基本情報 */}
      <div>
        <p className={sectionTitle}>基本情報</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>ID (snake_case)</Label>
            <Input {...register("id")} disabled={lockId} placeholder="rx_78_2" />
            <FieldError msg={errors.id?.message} />
          </div>
          <div>
            <Label>名前</Label>
            <Input {...register("name")} placeholder="RX-78-2 Gundam" />
            <FieldError msg={errors.name?.message} />
          </div>
          <div>
            <Label>価格 (C)</Label>
            <Input
              type="number"
              {...register("price", { valueAsNumber: true })}
            />
            <FieldError msg={errors.price?.message} />
          </div>
          <div>
            <Label>勢力</Label>
            <Controller
              control={control}
              name="faction"
              render={({ field }) => (
                <select
                  {...field}
                  className={`${inputCls} bg-[#0a0a0a]`}
                >
                  <option value="">— 選択なし —</option>
                  <option value="FEDERATION">FEDERATION</option>
                  <option value="ZEON">ZEON</option>
                </select>
              )}
            />
            <FieldError msg={errors.faction?.message} />
          </div>
          <div className="col-span-2">
            <Label>説明</Label>
            <textarea
              {...register("description")}
              rows={2}
              className={`${inputCls} resize-none`}
            />
            <FieldError msg={errors.description?.message} />
          </div>
        </div>
      </div>

      {/* スペック */}
      <div>
        <p className={sectionTitle}>スペック</p>
        <div className="grid grid-cols-3 gap-3">
          {(
            [
              ["specs.max_hp", "最大 HP"],
              ["specs.armor", "装甲"],
              ["specs.sensor_range", "索敵範囲"],
            ] as const
          ).map(([name, label]) => (
            <div key={name}>
              <Label>{label}</Label>
              <Input type="number" {...register(name, { valueAsNumber: true })} />
              <FieldError msg={
                name === "specs.max_hp" ? errors.specs?.max_hp?.message
                : name === "specs.armor" ? errors.specs?.armor?.message
                : errors.specs?.sensor_range?.message
              } />
            </div>
          ))}
          {(
            [
              ["specs.mobility", "機動性"],
              ["specs.beam_resistance", "ビーム耐性 (0-1)"],
              ["specs.physical_resistance", "実弾耐性 (0-1)"],
              ["specs.melee_aptitude", "格闘適性"],
              ["specs.shooting_aptitude", "射撃適性"],
              ["specs.accuracy_bonus", "命中補正"],
              ["specs.evasion_bonus", "回避補正"],
              ["specs.acceleration_bonus", "加速補正"],
              ["specs.turning_bonus", "旋回補正"],
            ] as const
          ).map(([name, label]) => (
            <div key={name}>
              <Label>{label}</Label>
              <Input type="number" step="0.01" {...register(name, { valueAsNumber: true })} />
              <FieldError msg={
                name === "specs.mobility" ? errors.specs?.mobility?.message
                : name === "specs.beam_resistance" ? errors.specs?.beam_resistance?.message
                : name === "specs.physical_resistance" ? errors.specs?.physical_resistance?.message
                : name === "specs.melee_aptitude" ? errors.specs?.melee_aptitude?.message
                : name === "specs.shooting_aptitude" ? errors.specs?.shooting_aptitude?.message
                : name === "specs.accuracy_bonus" ? errors.specs?.accuracy_bonus?.message
                : name === "specs.evasion_bonus" ? errors.specs?.evasion_bonus?.message
                : name === "specs.acceleration_bonus" ? errors.specs?.acceleration_bonus?.message
                : errors.specs?.turning_bonus?.message
              } />
            </div>
          ))}
        </div>
      </div>

      {/* 武装 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className={`${sectionTitle} flex-1`}>武装</p>
          <button
            type="button"
            onClick={() => append({ ...defaultWeapon })}
            className="text-xs text-[#00ff41] border border-[#00ff41]/40 px-2 py-0.5 hover:border-[#00ff41] ml-4"
          >
            + 追加
          </button>
        </div>
        {errors.specs?.weapons?.message && (
          <p className="text-xs text-red-400 mb-2">{errors.specs.weapons.message}</p>
        )}
        <div className="space-y-4">
          {fields.map((field, index) => (
            <div
              key={field.id}
              className="border border-[#00ff41]/20 p-3 bg-[#080808]"
            >
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-[#ffb000]/60">武器 #{index + 1}</span>
                {fields.length > 1 && (
                  <button
                    type="button"
                    onClick={() => remove(index)}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    削除
                  </button>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <Label>ID (snake_case)</Label>
                  <Input {...register(`specs.weapons.${index}.id`)} placeholder="beam_rifle" />
                  <FieldError msg={errors.specs?.weapons?.[index]?.id?.message} />
                </div>
                <div className="col-span-2">
                  <Label>名前</Label>
                  <Input {...register(`specs.weapons.${index}.name`)} placeholder="Beam Rifle" />
                  <FieldError msg={errors.specs?.weapons?.[index]?.name?.message} />
                </div>
                <div>
                  <Label>威力</Label>
                  <Input type="number" {...register(`specs.weapons.${index}.power`, { valueAsNumber: true })} />
                  <FieldError msg={errors.specs?.weapons?.[index]?.power?.message} />
                </div>
                <div>
                  <Label>射程</Label>
                  <Input type="number" {...register(`specs.weapons.${index}.range`, { valueAsNumber: true })} />
                  <FieldError msg={errors.specs?.weapons?.[index]?.range?.message} />
                </div>
                <div>
                  <Label>命中率 (%)</Label>
                  <Input type="number" {...register(`specs.weapons.${index}.accuracy`, { valueAsNumber: true })} />
                  <FieldError msg={errors.specs?.weapons?.[index]?.accuracy?.message} />
                </div>
                <div>
                  <Label>種別</Label>
                  <Controller
                    control={control}
                    name={`specs.weapons.${index}.type`}
                    render={({ field }) => (
                      <select {...field} className={`${inputCls} bg-[#0a0a0a]`}>
                        <option value="PHYSICAL">PHYSICAL</option>
                        <option value="BEAM">BEAM</option>
                      </select>
                    )}
                  />
                </div>
                <div>
                  <Label>最適射程</Label>
                  <Input type="number" step="0.1" {...register(`specs.weapons.${index}.optimal_range`, { valueAsNumber: true })} />
                </div>
                <div>
                  <Label>減衰係数</Label>
                  <Input type="number" step="0.01" {...register(`specs.weapons.${index}.decay_rate`, { valueAsNumber: true })} />
                </div>
                <div className="flex items-center gap-2 mt-3">
                  <Controller
                    control={control}
                    name={`specs.weapons.${index}.is_melee`}
                    render={({ field }) => (
                      <input
                        type="checkbox"
                        id={`is_melee_${index}`}
                        checked={field.value}
                        onChange={field.onChange}
                        className="accent-[#00ff41]"
                      />
                    )}
                  />
                  <label htmlFor={`is_melee_${index}`} className="text-xs text-[#00ff41]/80">
                    近接武器
                  </label>
                </div>
              </div>
            </div>
          ))}
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
