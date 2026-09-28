"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { MasterEnvironment } from "@/types/admin";
import {
  EnvironmentFormValues,
  OBSTACLE_DENSITIES,
  TERRAIN_GRADES,
  VIEWER_PRESETS,
  environmentFormSchema,
  toEnvironmentFormValues,
} from "@/lib/theater";

interface EnvironmentEditFormProps {
  /** 編集対象の環境タイプ。null なら新規作成 */
  initialData: MasterEnvironment | null;
  onSubmit: (values: EnvironmentFormValues) => Promise<void>;
  onCancel: () => void;
  isSubmitting?: boolean;
}

const inputCls =
  "w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41] disabled:opacity-50";

function Label({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs text-[#ffb000]/80 mb-0.5">{children}</label>;
}

function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return <p className="mt-0.5 text-xs text-red-400">{msg}</p>;
}

function Hint({ children }: { children: React.ReactNode }) {
  return <p className="mt-0.5 text-xs text-[#00ff41]/40">{children}</p>;
}

/** 環境タイプの新規追加・編集フォーム */
export default function EnvironmentEditForm({
  initialData,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: EnvironmentEditFormProps) {
  "use no memo";
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EnvironmentFormValues>({
    resolver: zodResolver(environmentFormSchema),
    defaultValues: toEnvironmentFormValues(initialData),
  });

  useEffect(() => {
    reset(toEnvironmentFormValues(initialData));
  }, [initialData, reset]);

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <Label>ID (UPPER_SNAKE_CASE)</Label>
          <input {...register("id")} disabled={initialData !== null} placeholder="DESERT" className={inputCls} />
          <FieldError msg={errors.id?.message} />
          <Hint>作成後は変更できない（機体の地形適正のキーになる）</Hint>
        </div>
        <div>
          <Label>表示名</Label>
          <input {...register("name")} placeholder="砂漠" className={inputCls} />
          <FieldError msg={errors.name?.message} />
        </div>
      </div>
      <div>
        <Label>説明</Label>
        <textarea {...register("description")} rows={2} className={inputCls} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <Label>索敵範囲の倍率</Label>
          <input
            type="number"
            step="0.01"
            {...register("sensor_range_multiplier", { valueAsNumber: true })}
            className={inputCls}
          />
          <FieldError msg={errors.sensor_range_multiplier?.message} />
          <Hint>0 より大きく 1 以下</Hint>
        </div>
        <div>
          <Label>射撃命中ペナルティ α</Label>
          <input
            type="number"
            step="0.01"
            {...register("ranged_accuracy_penalty", { valueAsNumber: true })}
            className={inputCls}
          />
          <FieldError msg={errors.ranged_accuracy_penalty?.message} />
          <Hint>0〜1。基準距離以上で射撃の命中率が (1 − α) 倍になる</Hint>
        </div>
        <div>
          <Label>基準距離 D (m)</Label>
          <input
            type="number"
            step="1"
            {...register("ranged_penalty_ref_distance", { valueAsNumber: true })}
            className={inputCls}
          />
          <FieldError msg={errors.ranged_penalty_ref_distance?.message} />
          <Hint>ペナルティが最大になる距離。0 より大きい</Hint>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <Label>障害物密度の既定値</Label>
          <select {...register("default_obstacle_density")} className={inputCls}>
            {OBSTACLE_DENSITIES.map((density) => (
              <option key={density} value={density}>
                {density}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label>地形適正の既定ランク</Label>
          <select {...register("default_terrain_grade")} className={inputCls}>
            {TERRAIN_GRADES.map((grade) => (
              <option key={grade} value={grade}>
                {grade}
              </option>
            ))}
          </select>
          <Hint>機体に地形適正の設定が無いときに使う</Hint>
        </div>
        <div>
          <Label>描画プリセット</Label>
          <select {...register("viewer_preset")} className={inputCls}>
            {VIEWER_PRESETS.map((preset) => (
              <option key={preset} value={preset}>
                {preset}
              </option>
            ))}
          </select>
        </div>
      </div>

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
