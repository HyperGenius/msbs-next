/* frontend/src/components/admin/WeaponEditForm.tsx */
"use client";

import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { MasterWeapon } from "@/types/battle";

// ============================================================
// Zod バリデーションスキーマ
// ============================================================

export const masterWeaponSchema = z.object({
  id: z
    .string()
    .min(1, "ID is required")
    .regex(/^[a-z0-9_]+$/, "ID must be lowercase alphanumeric with underscores (snake_case)"),
  name: z.string().min(1, "Name is required"),
  price: z.number({ message: "Must be a number" }).int().nonnegative("Must be ≥ 0"),
  description: z.string(),
  weapon: z.object({
    id: z
      .string()
      .min(1, "Weapon ID is required")
      .regex(/^[a-z0-9_]+$/, "Weapon ID must be snake_case alphanumeric"),
    name: z.string().min(1, "Weapon name is required"),
    power: z.number({ message: "Must be a number" }).int().positive("Must be > 0"),
    range: z.number({ message: "Must be a number" }).positive("Must be > 0"),
    accuracy: z.number({ message: "Must be a number" }).min(0).max(100, "Must be 0-100"),
    type: z.enum(["BEAM", "PHYSICAL"]),
    weapon_type: z.enum(["MELEE", "CLOSE_RANGE", "RANGED"]).optional(),
    optimal_range: z.number({ message: "Must be a number" }).nonnegative(),
    decay_rate: z.number({ message: "Must be a number" }).nonnegative(),
    is_melee: z.boolean(),
    max_ammo: z.number().int().nonnegative().nullable().optional(),
    en_cost: z.number({ message: "Must be a number" }).int().nonnegative().optional(),
    cooldown_sec: z.number({ message: "Must be a number" }).nonnegative().optional(),
    fire_arc_deg: z.number({ message: "Must be a number" }).nonnegative().optional(),
  }),
});

export type WeaponFormValues = z.infer<typeof masterWeaponSchema>;

// ============================================================
// コンポーネント
// ============================================================

interface WeaponEditFormProps {
  /** 編集対象武器（null の場合は新規作成モード） */
  initialData: MasterWeapon | null;
  /** id フィールドを編集不可にする（既存武器の更新時） */
  lockId?: boolean;
  onSubmit: (values: WeaponFormValues) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

const defaultValues: WeaponFormValues = {
  id: "",
  name: "",
  price: 300,
  description: "",
  weapon: {
    id: "",
    name: "",
    power: 150,
    range: 400,
    accuracy: 70,
    type: "PHYSICAL",
    weapon_type: "RANGED",
    optimal_range: 300,
    decay_rate: 0.08,
    is_melee: false,
    max_ammo: null,
    en_cost: 0,
    cooldown_sec: 1.0,
    fire_arc_deg: 30.0,
  },
};

function toFormValues(w: MasterWeapon): WeaponFormValues {
  return {
    id: w.id,
    name: w.name,
    price: w.price,
    description: w.description,
    weapon: {
      id: w.weapon.id,
      name: w.weapon.name,
      power: w.weapon.power,
      range: w.weapon.range,
      accuracy: w.weapon.accuracy,
      type: (w.weapon.type ?? "PHYSICAL") as "BEAM" | "PHYSICAL",
      weapon_type: (w.weapon.weapon_type ?? "RANGED") as "MELEE" | "CLOSE_RANGE" | "RANGED",
      optimal_range: w.weapon.optimal_range ?? 300,
      decay_rate: w.weapon.decay_rate ?? 0.08,
      is_melee: w.weapon.is_melee ?? false,
      max_ammo: w.weapon.max_ammo ?? null,
      en_cost: w.weapon.en_cost ?? 0,
      cooldown_sec: (w.weapon as { cooldown_sec?: number }).cooldown_sec ?? 1.0,
      fire_arc_deg: (w.weapon as { fire_arc_deg?: number }).fire_arc_deg ?? 30.0,
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

const inputCls =
  "w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41] disabled:opacity-50";

function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`${inputCls} ${className ?? ""}`}
    />
  );
}

export default function WeaponEditForm({
  initialData,
  lockId = false,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: WeaponEditFormProps) {
  const {
    register,
    handleSubmit,
    control,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<WeaponFormValues>({
    resolver: zodResolver(masterWeaponSchema),
    defaultValues: initialData ? toFormValues(initialData) : defaultValues,
  });

  useEffect(() => {
    reset(initialData ? toFormValues(initialData) : defaultValues);
  }, [initialData, reset]);

  // エントリー ID と武器 ID を同期する（新規作成時のみ）
  const watchId = watch("id");
  useEffect(() => {
    if (!lockId) {
      setValue("weapon.id", watchId);
    }
  }, [watchId, lockId, setValue]);

  const sectionTitle =
    "text-xs font-bold text-[#ffb000] uppercase tracking-wider mb-2 border-b border-[#ffb000]/20 pb-1";

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
            <Input {...register("id")} disabled={lockId} placeholder="beam_rifle" />
            <FieldError msg={errors.id?.message} />
          </div>
          <div>
            <Label>名前</Label>
            <Input {...register("name")} placeholder="Beam Rifle" />
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

      {/* 武器スペック */}
      <div>
        <p className={sectionTitle}>武器スペック</p>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label>武器 ID</Label>
            <Input {...register("weapon.id")} disabled placeholder="beam_rifle" />
            <FieldError msg={errors.weapon?.id?.message} />
          </div>
          <div className="col-span-2">
            <Label>武器名</Label>
            <Input {...register("weapon.name")} placeholder="Beam Rifle" />
            <FieldError msg={errors.weapon?.name?.message} />
          </div>
          <div>
            <Label>威力</Label>
            <Input type="number" {...register("weapon.power", { valueAsNumber: true })} />
            <FieldError msg={errors.weapon?.power?.message} />
          </div>
          <div>
            <Label>射程</Label>
            <Input type="number" {...register("weapon.range", { valueAsNumber: true })} />
            <FieldError msg={errors.weapon?.range?.message} />
          </div>
          <div>
            <Label>命中率 (%)</Label>
            <Input type="number" {...register("weapon.accuracy", { valueAsNumber: true })} />
            <FieldError msg={errors.weapon?.accuracy?.message} />
          </div>
          <div>
            <Label>属性 (type)</Label>
            <Controller
              control={control}
              name="weapon.type"
              render={({ field }) => (
                <select {...field} className={`${inputCls} bg-[#0a0a0a]`}>
                  <option value="PHYSICAL">PHYSICAL</option>
                  <option value="BEAM">BEAM</option>
                </select>
              )}
            />
            <FieldError msg={errors.weapon?.type?.message} />
          </div>
          <div>
            <Label>武器種別 (weapon_type)</Label>
            <Controller
              control={control}
              name="weapon.weapon_type"
              render={({ field }) => (
                <select {...field} value={field.value ?? "RANGED"} className={`${inputCls} bg-[#0a0a0a]`}>
                  <option value="RANGED">RANGED</option>
                  <option value="CLOSE_RANGE">CLOSE_RANGE</option>
                  <option value="MELEE">MELEE</option>
                </select>
              )}
            />
          </div>
          <div className="flex items-center gap-2 mt-3">
            <Controller
              control={control}
              name="weapon.is_melee"
              render={({ field }) => (
                <input
                  type="checkbox"
                  id="is_melee"
                  checked={field.value}
                  onChange={field.onChange}
                  className="accent-[#00ff41]"
                />
              )}
            />
            <label htmlFor="is_melee" className="text-xs text-[#00ff41]/80">
              近接武器 (is_melee)
            </label>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3 mt-3">
          <div>
            <Label>最適射程</Label>
            <Input
              type="number"
              step="0.1"
              {...register("weapon.optimal_range", { valueAsNumber: true })}
            />
            <FieldError msg={errors.weapon?.optimal_range?.message} />
          </div>
          <div>
            <Label>減衰率 (decay_rate)</Label>
            <Input
              type="number"
              step="0.01"
              {...register("weapon.decay_rate", { valueAsNumber: true })}
            />
            <FieldError msg={errors.weapon?.decay_rate?.message} />
          </div>
          <div>
            <Label>最大弾数 (max_ammo)</Label>
            <Input
              type="number"
              placeholder="空欄=無限"
              {...register("weapon.max_ammo", {
                setValueAs: (v) => (v === "" || v === null ? null : Number(v)),
              })}
            />
          </div>
          <div>
            <Label>EN消費 (en_cost)</Label>
            <Input
              type="number"
              {...register("weapon.en_cost", { valueAsNumber: true })}
            />
            <FieldError msg={errors.weapon?.en_cost?.message} />
          </div>
          <div>
            <Label>クールダウン秒 (cooldown_sec)</Label>
            <Input
              type="number"
              step="0.1"
              {...register("weapon.cooldown_sec", { valueAsNumber: true })}
            />
            <FieldError msg={errors.weapon?.cooldown_sec?.message} />
          </div>
          <div>
            <Label>射撃弧 (fire_arc_deg)</Label>
            <Input
              type="number"
              step="1"
              {...register("weapon.fire_arc_deg", { valueAsNumber: true })}
            />
            <FieldError msg={errors.weapon?.fire_arc_deg?.message} />
          </div>
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
