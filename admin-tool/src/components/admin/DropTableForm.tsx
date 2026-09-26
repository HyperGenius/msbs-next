"use client";

import { useEffect, useState } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  DROP_FACTIONS,
  DROP_FACTION_LABELS,
  DropTableFormValues,
  TARGET_TYPE_LABELS,
  dropChances,
  dropTableFormSchema,
  effectiveDropRate,
  entryFromMobileSuit,
  entryFromSummary,
  entryFromWeapon,
  formatChance,
  toDropTableFormValues,
  unobtainableBlueprints,
} from "@/lib/dropTable";
import { DropTableDetail, DropTableEntryDetail } from "@/types/admin";
import DropTableEntryRow, { EntryChances } from "@/components/admin/DropTableEntryRow";
import MasterMobileSuitSelect from "@/components/admin/MasterMobileSuitSelect";
import MasterWeaponSelect from "@/components/admin/MasterWeaponSelect";
import { SciFiButton, SciFiHeading } from "@/components/ui";

interface DropTableFormProps {
  /** 保存済みのテーブル。保存後の再取得で変わるとフォームを入れ直す */
  initialData: DropTableDetail;
  onSubmit: (values: DropTableFormValues) => Promise<void>;
  isSubmitting?: boolean;
}

const inputCls =
  "w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41]";

function Label({ children }: { children: React.ReactNode }) {
  return <label className="block text-xs text-[#ffb000]/80 mb-0.5">{children}</label>;
}

function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return <p className="mt-0.5 text-xs text-red-400">{msg}</p>;
}

export default function DropTableForm({ initialData, onSubmit, isSubmitting = false }: DropTableFormProps) {
  "use no memo";
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<DropTableFormValues>({
    resolver: zodResolver(dropTableFormSchema),
    defaultValues: toDropTableFormValues(initialData),
  });
  const { fields, append, remove } = useFieldArray({ control, name: "entries" });
  const [addError, setAddError] = useState<string | null>(null);

  useEffect(() => {
    reset(toDropTableFormValues(initialData));
  }, [initialData, reset]);

  const [dropRate, winRateMultiplier, entries] = useWatch({
    control,
    name: ["drop_rate", "win_rate_multiplier", "entries"],
  });
  const settings = { drop_rate: dropRate, win_rate_multiplier: winRateMultiplier };
  const watchedEntries = entries ?? [];
  const chancesByFaction = (isWin: boolean) =>
    DROP_FACTIONS.map((faction) => dropChances(watchedEntries, settings, isWin, faction));
  const winChances = chancesByFaction(true);
  const loseChances = chancesByFaction(false);
  const chancesOf = (index: number): EntryChances => ({
    win: winChances.map((byEntry) => byEntry[index]),
    lose: loseChances.map((byEntry) => byEntry[index]),
  });
  const unobtainable = unobtainableBlueprints(
    initialData,
    watchedEntries.map((entry) => entry.blueprint_id)
  );

  function addEntry(entry: DropTableEntryDetail) {
    if (watchedEntries.some((e) => e.blueprint_id === entry.blueprint_id)) {
      setAddError(`${entry.target_name} はすでにテーブルにある`);
      return;
    }
    setAddError(null);
    append(entry);
  }

  return (
    <form
      onSubmit={handleSubmit(async (values) => {
        setAddError(null);
        await onSubmit(values);
      })}
      className="space-y-6"
    >
      {/* テーブルの設定 */}
      <section className="space-y-3">
        <SciFiHeading level={3} className="text-base">
          テーブルの設定
        </SciFiHeading>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <Label>名前</Label>
            <input {...register("name")} className={inputCls} />
            <FieldError msg={errors.name?.message} />
          </div>
          <div>
            <Label>ドロップ率 drop_rate (0〜1)</Label>
            <input
              type="number"
              min={0}
              max={1}
              step="any"
              {...register("drop_rate", { valueAsNumber: true })}
              className={inputCls}
            />
            <FieldError msg={errors.drop_rate?.message} />
          </div>
          <div>
            <Label>勝利時の倍率 win_rate_multiplier (1以上)</Label>
            <input
              type="number"
              min={1}
              step="any"
              {...register("win_rate_multiplier", { valueAsNumber: true })}
              className={inputCls}
            />
            <FieldError msg={errors.win_rate_multiplier?.message} />
          </div>
        </div>
        <p className="text-xs text-[#00ff41]/70">
          1回のバトルで何かがドロップする確率: 勝利時 {formatChance(effectiveDropRate(settings, true))} / 敗北時{" "}
          {formatChance(effectiveDropRate(settings, false))}
        </p>
      </section>

      {/* エントリー */}
      <section className="space-y-3">
        <SciFiHeading level={3} className="text-base">
          エントリー（{fields.length}件）
        </SciFiHeading>
        <p className="text-xs text-[#00ff41]/50">
          出現率は1回のバトルでその設計図が出る確率。勢力で購入できない機体は抽選対象から外れる。「—」は抽選対象外。
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-[#00ff41]/30 text-[#ffb000]/80">
                <th rowSpan={2} className="px-2 py-1 text-left">設計図</th>
                <th rowSpan={2} className="px-2 py-1 text-left">重み</th>
                <th rowSpan={2} className="px-2 py-1">勝利時のみ</th>
                <th colSpan={DROP_FACTIONS.length} className="px-2 py-1">勝利時</th>
                <th colSpan={DROP_FACTIONS.length} className="px-2 py-1">敗北時</th>
                <th rowSpan={2} />
              </tr>
              <tr className="border-b border-[#00ff41]/30 text-[#ffb000]/60">
                {[...DROP_FACTIONS, ...DROP_FACTIONS].map((faction, i) => (
                  <th key={i} className="px-2 py-1 text-right">
                    {DROP_FACTION_LABELS[faction]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {fields.map((field, index) => (
                <DropTableEntryRow
                  key={field.id}
                  index={index}
                  entry={field}
                  register={register}
                  chances={chancesOf(index)}
                  weightError={errors.entries?.[index]?.weight?.message}
                  onRemove={() => remove(index)}
                />
              ))}
              {fields.length === 0 && (
                <tr>
                  <td colSpan={4 + DROP_FACTIONS.length * 2} className="px-2 py-6 text-center text-[#00ff41]/40">
                    エントリーが無い。保存するとドロップしなくなる
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <MasterMobileSuitSelect buttonLabel="機体を追加" onApply={(ms) => addEntry(entryFromMobileSuit(ms))} />
          <MasterWeaponSelect buttonLabel="武器を追加" onApply={(w) => addEntry(entryFromWeapon(w))} />
        </div>
        <FieldError msg={addError ?? undefined} />
      </section>

      {/* 入手手段の無い設計図 */}
      <section className="space-y-2">
        <SciFiHeading level={3} className="text-base">
          入手手段の無い要設計図（{unobtainable.length}件）
        </SciFiHeading>
        <p className="text-xs text-[#00ff41]/50">
          標準配備ではないのに、このテーブルに入っていない機体・武器。プレイヤーは購入できない。
        </p>
        {unobtainable.length === 0 ? (
          <p className="text-xs text-[#00ff41]/40">なし</p>
        ) : (
          <ul className="space-y-1">
            {unobtainable.map((summary) => (
              <li key={summary.blueprint_id} className="flex items-center gap-2 text-xs">
                <span className="text-[10px] px-1 border border-[#ffb000]/40 text-[#ffb000]">
                  {TARGET_TYPE_LABELS[summary.target_type]}
                </span>
                <span className="text-[#ffb000]">{summary.target_name}</span>
                <span className="text-[#00ff41]/40">{summary.blueprint_id}</span>
                <button
                  type="button"
                  onClick={() => addEntry(entryFromSummary(summary))}
                  className="ml-auto text-xs text-[#00ff41] border border-[#00ff41]/40 px-2 hover:border-[#00ff41]"
                >
                  テーブルに追加
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="flex items-center gap-3 border-t border-[#00ff41]/20 pt-4">
        <SciFiButton type="submit" disabled={isSubmitting}>
          {isSubmitting ? "保存中..." : "保存"}
        </SciFiButton>
        <SciFiButton
          type="button"
          variant="secondary"
          disabled={!isDirty || isSubmitting}
          onClick={() => {
            setAddError(null);
            reset();
          }}
        >
          変更を破棄
        </SciFiButton>
        {isDirty && <span className="text-xs text-[#ffb000]">未保存の変更がある</span>}
        {initialData.id === null && (
          <span className="text-xs text-[#ffb000]/70">テーブルは未作成。保存すると作成される</span>
        )}
      </div>
    </form>
  );
}
