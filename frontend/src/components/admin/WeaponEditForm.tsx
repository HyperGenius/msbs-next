/* frontend/src/components/admin/WeaponEditForm.tsx */
"use client";

import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { MasterWeaponEntry } from "@/types/battle";

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
    cool_down_turn: z.number({ message: "Must be a number" }).int().nonnegative().optional(),
    cooldown_sec: z.number({ message: "Must be a number" }).nonnegative().optional(),
    fire_arc_deg: z.number({ message: "Must be a number" }).min(0).max(360).optional(),
  }),
});

export type WeaponFormValues = z.infer<typeof masterWeaponSchema>;

// ============================================================
// コンポーネント
// ============================================================

interface WeaponEditFormProps {
  /** 編集対象武器（null の場合は新規作成モード） */
  initialData: MasterWeaponEntry | null;
  /** idフィールドを編集不可にする（既存武器の更新時） */
  lockId?: boolean;
  onSubmit: (values: WeaponFormValues) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

const defaultValues: WeaponFormValues = {
  id: "",
  name: "",
  price: 500,
  description: "",
  weapon: {
    id: "",
    name: "",
    power: 100,
    range: 400,
    accuracy: 60,
    type: "PHYSICAL",
    weapon_type: "RANGED",
    optimal_range: 300,
    decay_rate: 0.08,
    is_melee: false,
    max_ammo: null,
    en_cost: 0,
    cool_down_turn: 0,
    cooldown_sec: 1.0,
    fire_arc_deg: 30.0,
  },
};

// ============================================================
// UIパーツ
// ============================================================

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label className="block text-xs text-[#ffb000]/80 mb-1">{children}</label>
  );
}

function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1.5 text-sm font-mono focus:outline-none focus:border-[#00ff41] disabled:opacity-50 ${props.className ?? ""}`}
    />
  );
}

function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1.5 text-sm font-mono focus:outline-none focus:border-[#00ff41] ${props.className ?? ""}`}
    />
  );
}

function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return <p className="mt-0.5 text-xs text-red-400">{msg}</p>;
}

// ============================================================
// メインコンポーネント
// ============================================================

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
    reset,
    control,
    formState: { errors },
  } = useForm<WeaponFormValues>({
    resolver: zodResolver(masterWeaponSchema),
    defaultValues,
  });

  useEffect(() => {
    if (initialData) {
      reset({
        id: initialData.id,
        name: initialData.name,
        price: initialData.price,
        description: initialData.description,
        weapon: {
          id: initialData.weapon.id,
          name: initialData.weapon.name,
          power: initialData.weapon.power,
          range: initialData.weapon.range,
          accuracy: initialData.weapon.accuracy,
          type: (initialData.weapon.type as "BEAM" | "PHYSICAL") ?? "PHYSICAL",
          weapon_type: (initialData.weapon.weapon_type as "MELEE" | "CLOSE_RANGE" | "RANGED") ?? "RANGED",
          optimal_range: initialData.weapon.optimal_range ?? 300,
          decay_rate: initialData.weapon.decay_rate ?? 0.08,
          is_melee: initialData.weapon.is_melee ?? false,
          max_ammo: initialData.weapon.max_ammo ?? null,
          en_cost: initialData.weapon.en_cost ?? 0,
          cool_down_turn: initialData.weapon.cool_down_turn ?? 0,
          cooldown_sec: (initialData.weapon as { cooldown_sec?: number }).cooldown_sec ?? 1.0,
          fire_arc_deg: (initialData.weapon as { fire_arc_deg?: number }).fire_arc_deg ?? 30.0,
        },
      });
    } else {
      reset(defaultValues);
    }
  }, [initialData, reset]);

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 text-[#00ff41] font-mono">
      {/* エントリー基本情報 */}
      <div className="space-y-3">
        <p className="text-xs text-[#ffb000]/60 uppercase tracking-widest">基本情報</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>ID (snake_case)</Label>
            <Input
              {...register("id")}
              placeholder="beam_rifle"
              disabled={lockId}
            />
            <FieldError msg={errors.id?.message} />
          </div>
          <div>
            <Label>価格 (C)</Label>
            <Input
              type="number"
              {...register("price", { valueAsNumber: true })}
              placeholder="800"
            />
            <FieldError msg={errors.price?.message} />
          </div>
        </div>
        <div>
          <Label>エントリー名</Label>
          <Input {...register("name")} placeholder="Beam Rifle" />
          <FieldError msg={errors.name?.message} />
        </div>
        <div>
          <Label>説明</Label>
          <Input {...register("description")} placeholder="武器の説明..." />
          <FieldError msg={errors.description?.message} />
        </div>
      </div>

      {/* 武器パラメータ */}
      <div className="border border-[#00ff41]/20 p-3 bg-[#080808] space-y-3">
        <p className="text-xs text-[#ffb000]/60 uppercase tracking-widest">武器パラメータ</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>武器ID (snake_case)</Label>
            <Input {...register("weapon.id")} placeholder="beam_rifle" />
            <FieldError msg={errors.weapon?.id?.message} />
          </div>
          <div>
            <Label>武器名</Label>
            <Input {...register("weapon.name")} placeholder="Beam Rifle" />
            <FieldError msg={errors.weapon?.name?.message} />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label>威力</Label>
            <Input
              type="number"
              {...register("weapon.power", { valueAsNumber: true })}
            />
            <FieldError msg={errors.weapon?.power?.message} />
          </div>
          <div>
            <Label>射程</Label>
            <Input
              type="number"
              step="any"
              {...register("weapon.range", { valueAsNumber: true })}
            />
            <FieldError msg={errors.weapon?.range?.message} />
          </div>
          <div>
            <Label>命中率 (%)</Label>
            <Input
              type="number"
              step="any"
              {...register("weapon.accuracy", { valueAsNumber: true })}
            />
            <FieldError msg={errors.weapon?.accuracy?.message} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>武器属性 (type)</Label>
            <Controller
              name="weapon.type"
              control={control}
              render={({ field }) => (
                <Select {...field}>
                  <option value="BEAM">BEAM</option>
                  <option value="PHYSICAL">PHYSICAL</option>
                </Select>
              )}
            />
            <FieldError msg={errors.weapon?.type?.message} />
          </div>
          <div>
            <Label>武器種別 (weapon_type)</Label>
            <Controller
              name="weapon.weapon_type"
              control={control}
              render={({ field }) => (
                <Select {...field} value={field.value ?? "RANGED"}>
                  <option value="RANGED">RANGED</option>
                  <option value="CLOSE_RANGE">CLOSE_RANGE</option>
                  <option value="MELEE">MELEE</option>
                </Select>
              )}
            />
            <FieldError msg={errors.weapon?.weapon_type?.message} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>最適射程</Label>
            <Input
              type="number"
              step="any"
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
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label>最大弾数 (空=無限)</Label>
            <Input
              type="number"
              step="1"
              placeholder="空=無限"
              {...register("weapon.max_ammo", {
                setValueAs: (v) => (v === "" || v === null ? null : Number(v)),
              })}
            />
            <FieldError msg={errors.weapon?.max_ammo?.message} />
          </div>
          <div>
            <Label>EN消費</Label>
            <Input
              type="number"
              step="1"
              {...register("weapon.en_cost", { valueAsNumber: true })}
            />
            <FieldError msg={errors.weapon?.en_cost?.message} />
          </div>
          <div>
            <Label>クールダウン (秒)</Label>
            <Input
              type="number"
              step="0.1"
              {...register("weapon.cooldown_sec", { valueAsNumber: true })}
            />
            <FieldError msg={errors.weapon?.cooldown_sec?.message} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>射撃弧 (fire_arc_deg)</Label>
            <Input
              type="number"
              step="1"
              {...register("weapon.fire_arc_deg", { valueAsNumber: true })}
            />
            <FieldError msg={errors.weapon?.fire_arc_deg?.message} />
          </div>
          <div className="flex items-center gap-3 mt-4">
            <Controller
              name="weapon.is_melee"
              control={control}
              render={({ field }) => (
                <input
                  type="checkbox"
                  id="is_melee"
                  checked={field.value}
                  onChange={(e) => field.onChange(e.target.checked)}
                  className="w-4 h-4 accent-[#ffb000]"
                />
              )}
            />
            <label htmlFor="is_melee" className="text-sm cursor-pointer select-none">
              近接武器 (is_melee)
            </label>
            <FieldError msg={errors.weapon?.is_melee?.message} />
          </div>
        </div>
      </div>

      {/* 送信ボタン */}
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
          className="flex-1 border border-[#00ff41]/30 text-[#00ff41]/60 py-2 text-sm hover:border-[#00ff41]/60 transition-colors"
        >
          キャンセル
        </button>
      </div>
    </form>
  );
}
