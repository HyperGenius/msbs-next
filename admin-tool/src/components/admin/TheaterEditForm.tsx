"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { MasterEnvironment, MasterTheater } from "@/types/admin";
import {
  OBSTACLE_DENSITIES,
  TheaterFormValues,
  formatMinovskyRange,
  theaterFormSchema,
  toTheaterFormValues,
} from "@/lib/theater";

interface TheaterEditFormProps {
  /**
   * 編集対象の戦域。null なら新規作成。
   * 入力中の値を保つため、値が変わってもフォームは初期化しない。編集対象を替えるときは key を変える。
   */
  initialData: MasterTheater | null;
  /** 新規作成の順番の初期値を決めるのに使う */
  theaters: MasterTheater[];
  environments: MasterEnvironment[];
  onSubmit: (values: TheaterFormValues) => Promise<void>;
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

/** 戦域の新規追加・編集フォーム */
export default function TheaterEditForm({
  initialData,
  theaters,
  environments,
  onSubmit,
  onCancel,
  isSubmitting = false,
}: TheaterEditFormProps) {
  "use no memo";
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<TheaterFormValues>({
    resolver: zodResolver(theaterFormSchema),
    defaultValues: toTheaterFormValues(initialData, theaters),
  });

  const base = watch("base_minovsky");
  const variance = watch("minovsky_variance");
  const environmentId = watch("environment_id");
  const environment = environments.find((e) => e.id === environmentId);

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <Label>ID (snake_case)</Label>
          <input {...register("id")} disabled={initialData !== null} placeholder="odessa" className={inputCls} />
          <FieldError msg={errors.id?.message} />
          <Hint>作成後は変更できない</Hint>
        </div>
        <div>
          <Label>表示名</Label>
          <input {...register("name")} placeholder="オデッサ" className={inputCls} />
          <FieldError msg={errors.name?.message} />
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <Label>環境タイプ</Label>
          <select {...register("environment_id")} className={inputCls}>
            <option value="">— 選択 —</option>
            {environments.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name} ({e.id})
              </option>
            ))}
          </select>
          <FieldError msg={errors.environment_id?.message} />
        </div>
        <div>
          <Label>障害物密度</Label>
          <select {...register("obstacle_density")} className={inputCls}>
            <option value="">
              環境タイプの既定値{environment ? `（${environment.default_obstacle_density}）` : ""}
            </option>
            {OBSTACLE_DENSITIES.map((density) => (
              <option key={density} value={density}>
                {density}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <Label>ミノフスキー濃度の基準値</Label>
          <input type="number" step="0.01" {...register("base_minovsky", { valueAsNumber: true })} className={inputCls} />
          <FieldError msg={errors.base_minovsky?.message} />
          <Hint>0〜1</Hint>
        </div>
        <div>
          <Label>揺らぎ幅</Label>
          <input
            type="number"
            step="0.01"
            {...register("minovsky_variance", { valueAsNumber: true })}
            className={inputCls}
          />
          <FieldError msg={errors.minovsky_variance?.message} />
          <Hint>
            0〜0.5
            {Number.isFinite(base) && Number.isFinite(variance) &&
              `。開催日ごとに ${formatMinovskyRange({ base_minovsky: base, minovsky_variance: variance })} の値になる`}
          </Hint>
        </div>
      </div>
      <div>
        <Label>予報のヒント</Label>
        <input {...register("hint")} placeholder="格闘・索敵に強い機体が有利" className={inputCls} />
      </div>
      <div>
        <Label>説明（フレーバーテキスト）</Label>
        <textarea {...register("description")} rows={2} className={inputCls} />
      </div>
      {initialData === null ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <Label>ローテーション順</Label>
            <input type="number" step="1" {...register("rotation_order", { valueAsNumber: true })} className={inputCls} />
            <FieldError msg={errors.rotation_order?.message} />
            <Hint>昇順に巡回する。間に追加できるよう10刻みにする</Hint>
          </div>
          <div className="flex items-center gap-2 mt-5">
            <input type="checkbox" id="theater_is_active" {...register("is_active")} className="accent-[#00ff41]" />
            <label htmlFor="theater_is_active" className="text-xs text-[#00ff41]/80">
              ローテーションに含める
            </label>
          </div>
        </div>
      ) : (
        <Hint>ローテーション順と有効化は、一覧で変更する</Hint>
      )}

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
