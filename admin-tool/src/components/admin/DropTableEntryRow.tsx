"use client";

import { UseFormRegister } from "react-hook-form";
import { DropTableFormValues, TARGET_TYPE_LABELS, formatChance } from "@/lib/dropTable";
import { DropTableEntryDetail } from "@/types/admin";
import { BlueprintBadge } from "@/components/admin/BlueprintSettingsFields";

/** 勝敗ごとの、勢力別の出現率。並びは DROP_FACTIONS と同じ */
export interface EntryChances {
  win: (number | null)[];
  lose: (number | null)[];
}

interface DropTableEntryRowProps {
  index: number;
  entry: DropTableEntryDetail;
  register: UseFormRegister<DropTableFormValues>;
  chances: EntryChances;
  weightError?: string;
  onRemove: () => void;
}

const cellCls = "px-2 py-1.5 align-top";

export default function DropTableEntryRow({
  index,
  entry,
  register,
  chances,
  weightError,
  onRemove,
}: DropTableEntryRowProps) {
  return (
    <tr className="border-b border-[#00ff41]/10">
      <td className={cellCls}>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] px-1 border border-[#00ff41]/30 text-[#00ff41]/70">
            {TARGET_TYPE_LABELS[entry.target_type]}
          </span>
          <span className="font-bold">{entry.target_name}</span>
          <BlueprintBadge
            blueprint={{ is_standard_issue: entry.is_standard_issue, duplicate_credit_value: 0 }}
          />
        </div>
        <p className="text-[10px] text-[#00ff41]/40">
          {entry.blueprint_id}
          {entry.faction && ` / ${entry.faction}`}
        </p>
        {entry.is_standard_issue && (
          <p className="text-[10px] text-[#ffb000]">
            ⚠ 標準配備のため設計図なしで購入できる。ドロップしても換金されるだけになる
          </p>
        )}
      </td>
      <td className={cellCls}>
        <input
          type="number"
          min={1}
          step={1}
          aria-label={`${entry.target_name} の重み`}
          {...register(`entries.${index}.weight`, { valueAsNumber: true })}
          className="w-16 bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41]"
        />
        {weightError && <p className="text-[10px] text-red-400">{weightError}</p>}
      </td>
      <td className={`${cellCls} text-center`}>
        <input
          type="checkbox"
          aria-label={`${entry.target_name} を勝利時のみにする`}
          {...register(`entries.${index}.requires_win`)}
          className="accent-[#00ff41] mt-2"
        />
      </td>
      {[...chances.win, ...chances.lose].map((chance, i) => (
        <td
          key={i}
          className={`${cellCls} text-right tabular-nums ${chance === null ? "text-[#00ff41]/30" : ""}`}
        >
          {formatChance(chance)}
        </td>
      ))}
      <td className={cellCls}>
        <button
          type="button"
          onClick={onRemove}
          className="text-xs text-red-400 border border-red-500/40 px-2 py-0.5 hover:border-red-500"
        >
          削除
        </button>
      </td>
    </tr>
  );
}
