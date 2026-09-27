"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { MasterTechnology } from "@/types/admin";
import {
  TechnologyFormValues,
  maxLevelOf,
  parseThresholds,
  technologyFormSchema,
  thresholdsError,
  toTechnologyFormValues,
} from "@/lib/technology";

interface TechnologyEditFormProps {
  /** 編集対象の技術。null なら新規作成 */
  initialData: MasterTechnology | null;
  onSubmit: (values: TechnologyFormValues) => Promise<void>;
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

/** 技術マスターの新規追加・編集フォーム */
export default function TechnologyEditForm({
  initialData,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: TechnologyEditFormProps) {
  "use no memo";
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<TechnologyFormValues>({
    resolver: zodResolver(technologyFormSchema),
    defaultValues: toTechnologyFormValues(initialData),
  });

  useEffect(() => {
    reset(toTechnologyFormValues(initialData));
  }, [initialData, reset]);

  const thresholds = parseThresholds(watch("level_thresholds") ?? "");
  const previewable = thresholdsError(thresholds) === null;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <Label>ID (snake_case)</Label>
          <input {...register("id")} disabled={initialData !== null} className={inputCls} />
          <FieldError msg={errors.id?.message} />
          <p className="mt-0.5 text-xs text-[#00ff41]/40">
            機体の beam_generator_lv と紛らわしい名前にしない（例: beam_generator_tech）
          </p>
        </div>
        <div>
          <Label>表示名</Label>
          <input {...register("name")} className={inputCls} />
          <FieldError msg={errors.name?.message} />
        </div>
      </div>
      <div>
        <Label>説明</Label>
        <textarea {...register("description")} rows={2} className={inputCls} />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <Label>Lvごとの累計断片数（カンマ区切り）</Label>
          <input {...register("level_thresholds")} placeholder="3, 8, 15" className={inputCls} />
          <FieldError msg={errors.level_thresholds?.message} />
          {previewable && (
            <p className="mt-0.5 text-xs text-[#00ff41]/60">
              最大Lv{maxLevelOf({ level_thresholds: thresholds })}:{" "}
              {thresholds.map((t, i) => `Lv${i + 1}=${t}個`).join(" / ")}
            </p>
          )}
          <p className="mt-0.5 text-xs text-[#00ff41]/40">
            閾値を上げると、既存プレイヤーのLvが下がることがある（購入済みの機体・武器は残る）
          </p>
        </div>
        <div>
          <Label>最大Lv後の換金額 (C)</Label>
          <input
            type="number"
            min={0}
            {...register("overflow_credit_value", { valueAsNumber: true })}
            className={inputCls}
          />
          <FieldError msg={errors.overflow_credit_value?.message} />
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
