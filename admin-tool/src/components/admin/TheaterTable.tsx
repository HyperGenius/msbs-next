"use client";

import { useState } from "react";
import { MasterEnvironment, MasterTheater } from "@/types/admin";
import { formatMinovskyRange } from "@/lib/theater";

interface TheaterTableProps {
  theaters: MasterTheater[];
  environments: MasterEnvironment[];
  selectedId: string | null;
  onSelect: (theater: MasterTheater) => void;
  onDelete: (theater: MasterTheater) => void;
  onChangeOrder: (theater: MasterTheater, rotationOrder: number) => Promise<void>;
  onToggleActive: (theater: MasterTheater, isActive: boolean) => Promise<void>;
}

const thClass = "px-2 py-1 text-left text-[#ffb000]/80 font-normal";
const tdClass = "px-2 py-1.5";

/**
 * 順番の入力欄。確定（フォーカスを外す・Enter）したときだけ保存する。
 * 保存済みの値が変わったら、呼び出し側が key を変えて作り直す。
 */
function RotationOrderInput({
  theater,
  onChange,
}: {
  theater: MasterTheater;
  onChange: (theater: MasterTheater, rotationOrder: number) => Promise<void>;
}) {
  const [draft, setDraft] = useState(String(theater.rotation_order));

  function commit() {
    const value = Number(draft);
    if (draft.trim() === "" || !Number.isInteger(value)) {
      setDraft(String(theater.rotation_order));
      return;
    }
    if (value !== theater.rotation_order) {
      onChange(theater, value).catch(() => setDraft(String(theater.rotation_order)));
    }
  }

  return (
    <input
      type="number"
      step={1}
      value={draft}
      onClick={(e) => e.stopPropagation()}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
      }}
      className="w-16 bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-1 py-0.5 text-xs font-mono text-right focus:outline-none focus:border-[#00ff41]"
    />
  );
}

/** 戦域の一覧。順番と有効化はこの表で変える。行を押すと編集対象にする */
export default function TheaterTable({
  theaters,
  environments,
  selectedId,
  onSelect,
  onDelete,
  onChangeOrder,
  onToggleActive,
}: TheaterTableProps) {
  if (theaters.length === 0) {
    return <p className="py-6 text-center text-xs text-[#00ff41]/40">戦域が無い</p>;
  }

  const environmentName = (id: string) => environments.find((e) => e.id === id)?.name ?? id;
  const activeCount = theaters.filter((t) => t.is_active).length;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-[#00ff41]/30">
            <th className={thClass}>順番</th>
            <th className={thClass}>有効</th>
            <th className={thClass}>戦域</th>
            <th className={thClass}>環境</th>
            <th className={thClass}>ミノフスキー濃度</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {theaters.map((theater) => {
            const isLastActive = theater.is_active && activeCount === 1;
            return (
              <tr
                key={theater.id}
                onClick={() => onSelect(theater)}
                className={`border-b border-[#00ff41]/10 cursor-pointer hover:bg-[#00ff41]/5 ${
                  theater.id === selectedId ? "bg-[#00ff41]/10" : ""
                } ${theater.is_active ? "" : "opacity-50"}`}
              >
                <td className={tdClass}>
                  <RotationOrderInput
                    key={`${theater.id}:${theater.rotation_order}`}
                    theater={theater}
                    onChange={onChangeOrder}
                  />
                </td>
                <td className={tdClass}>
                  <input
                    type="checkbox"
                    checked={theater.is_active}
                    disabled={isLastActive}
                    title={isLastActive ? "最後の有効な戦域は無効にできない" : undefined}
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => {
                      onToggleActive(theater, e.target.checked).catch(() => undefined);
                    }}
                    className="accent-[#00ff41] disabled:opacity-40"
                  />
                </td>
                <td className={tdClass}>
                  <p className="font-bold">{theater.name}</p>
                  <p className="text-[10px] text-[#00ff41]/40">{theater.id}</p>
                </td>
                <td className={tdClass}>
                  {environmentName(theater.environment_id)}
                  {theater.obstacle_density && (
                    <span className="ml-1 text-[#00ff41]/40">（障害物 {theater.obstacle_density}）</span>
                  )}
                </td>
                <td className={tdClass}>{formatMinovskyRange(theater)}</td>
                <td className={tdClass}>
                  <button
                    type="button"
                    disabled={isLastActive}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(theater);
                    }}
                    className="text-xs text-red-400 border border-red-500/40 px-2 py-0.5 hover:border-red-500 disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    削除
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
