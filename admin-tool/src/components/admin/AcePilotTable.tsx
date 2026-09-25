/* admin-tool/src/components/admin/AcePilotTable.tsx */
"use client";

import { useState } from "react";
import { AcePilot } from "@/types/admin";

interface AcePilotTableProps {
  acePilots: AcePilot[];
  selectedId: string | null;
  onSelect: (ace: AcePilot) => void;
  onDelete: (ace: AcePilot) => void;
}

type SortKey = "id" | "name" | "pilot_name" | "personality" | "max_hp" | "mobility" | "bounty_exp" | "bounty_credits";
type SortDir = "asc" | "desc";

const PERSONALITY_BADGE: Record<string, string> = {
  AGGRESSIVE: "bg-red-900/40 text-red-300 border border-red-700/40",
  CAUTIOUS: "bg-blue-900/40 text-blue-300 border border-blue-700/40",
  SNIPER: "bg-purple-900/40 text-purple-300 border border-purple-700/40",
};

function sortValue(ace: AcePilot, key: SortKey): string | number {
  if (key === "max_hp") return ace.mobile_suit.max_hp;
  if (key === "mobility") return ace.mobile_suit.mobility;
  return ace[key];
}

export default function AcePilotTable({ acePilots, selectedId, onSelect, onDelete }: AcePilotTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("id");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [filter, setFilter] = useState("");

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const q = filter.toLowerCase();
  const filtered = acePilots.filter(
    (ace) =>
      ace.id.toLowerCase().includes(q) ||
      ace.name.toLowerCase().includes(q) ||
      ace.pilot_name.toLowerCase().includes(q) ||
      ace.mobile_suit.name.toLowerCase().includes(q) ||
      ace.personality.toLowerCase().includes(q)
  );

  const sorted = [...filtered].sort((a, b) => {
    const av = sortValue(a, sortKey);
    const bv = sortValue(b, sortKey);
    if (av < bv) return sortDir === "asc" ? -1 : 1;
    if (av > bv) return sortDir === "asc" ? 1 : -1;
    return 0;
  });

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return <span className="text-[#00ff41]/30 ml-1">⇅</span>;
    return <span className="text-[#ffb000] ml-1">{sortDir === "asc" ? "↑" : "↓"}</span>;
  }

  const thClass =
    "px-3 py-2 text-left text-xs font-bold uppercase tracking-wider cursor-pointer select-none text-[#ffb000]/80 hover:text-[#ffb000] whitespace-nowrap";
  const tdClass = "px-3 py-2 text-sm whitespace-nowrap";

  const columns: [SortKey, string][] = [
    ["id", "ID"],
    ["name", "二つ名"],
    ["pilot_name", "パイロット"],
    ["personality", "性格"],
    ["max_hp", "HP"],
    ["mobility", "機動性"],
    ["bounty_exp", "賞金EXP"],
    ["bounty_credits", "賞金C"],
  ];

  return (
    <div className="space-y-3">
      <input
        type="text"
        placeholder="Filter by id / name / pilot / mobile suit..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] placeholder-[#00ff41]/40 px-3 py-2 text-sm font-mono focus:outline-none focus:border-[#00ff41]"
      />
      <div className="overflow-x-auto border border-[#00ff41]/20">
        <table className="min-w-full text-[#00ff41] font-mono">
          <thead className="bg-[#0a0a0a] border-b border-[#00ff41]/20">
            <tr>
              {columns.map(([key, label]) => (
                <th key={key} className={thClass} onClick={() => handleSort(key)}>
                  {label} <SortIcon k={key} />
                </th>
              ))}
              <th className={`${thClass} cursor-default`}>操作</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((ace) => {
              const isSelected = ace.id === selectedId;
              return (
                <tr
                  key={ace.id}
                  onClick={() => onSelect(ace)}
                  className={`cursor-pointer border-b border-[#00ff41]/10 transition-colors ${
                    isSelected ? "bg-[#00ff41]/10 border-[#00ff41]/40" : "hover:bg-[#00ff41]/5"
                  }`}
                >
                  <td className={`${tdClass} text-[#00ff41]/60`}>{ace.id}</td>
                  <td className={`${tdClass} font-bold ${isSelected ? "text-[#ffb000]" : ""}`}>{ace.name}</td>
                  <td className={tdClass}>
                    {ace.pilot_name}
                    <span className="block text-xs text-[#00ff41]/50">{ace.mobile_suit.name}</span>
                  </td>
                  <td className={tdClass}>
                    <span className={`px-2 py-0.5 text-xs font-bold ${PERSONALITY_BADGE[ace.personality] ?? ""}`}>
                      {ace.personality}
                    </span>
                  </td>
                  <td className={tdClass}>{ace.mobile_suit.max_hp}</td>
                  <td className={tdClass}>{ace.mobile_suit.mobility.toFixed(2)}</td>
                  <td className={tdClass}>{ace.bounty_exp}</td>
                  <td className={tdClass}>{ace.bounty_credits.toLocaleString()} C</td>
                  <td className={tdClass} onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => onDelete(ace)}
                      className="text-xs text-red-400 hover:text-red-300 border border-red-700/40 px-2 py-0.5 hover:border-red-500/60 transition-colors"
                    >
                      削除
                    </button>
                  </td>
                </tr>
              );
            })}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={columns.length + 1} className="text-center text-[#00ff41]/40 py-8 text-sm">
                  エースパイロットが見つかりません
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-[#00ff41]/40 text-right">
        {sorted.length} / {acePilots.length} 体表示中
      </p>
    </div>
  );
}
