/* frontend/src/components/admin/MobileSuitTable.tsx */
"use client";

import { useState } from "react";
import { MasterMobileSuit } from "@/types/admin";
import { BlueprintFilter, matchesBlueprintFilter } from "@/lib/blueprint";
import { BlueprintBadge, BlueprintFilterSelect } from "./BlueprintSettingsFields";

interface MobileSuitTableProps {
  mobileSuits: MasterMobileSuit[];
  selectedId: string | null;
  onSelect: (ms: MasterMobileSuit) => void;
  onDelete: (ms: MasterMobileSuit) => void;
}

type SortKey =
  | "id"
  | "model_number"
  | "name"
  | "faction"
  | "price"
  | "duplicate_credit_value"
  | "max_hp"
  | "armor"
  | "mobility";
type SortDir = "asc" | "desc";

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="text-[#00ff41]/30 ml-1">⇅</span>;
  return <span className="text-[#ffb000] ml-1">{dir === "asc" ? "↑" : "↓"}</span>;
}

export default function MobileSuitTable({
  mobileSuits,
  selectedId,
  onSelect,
  onDelete,
}: MobileSuitTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [filter, setFilter] = useState("");
  const [blueprintFilter, setBlueprintFilter] = useState<BlueprintFilter>("all");

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const filtered = mobileSuits.filter(
    (ms) =>
      matchesBlueprintFilter(ms.blueprint, blueprintFilter) &&
      (ms.name.toLowerCase().includes(filter.toLowerCase()) ||
        ms.name_ja?.toLowerCase().includes(filter.toLowerCase()) ||
        ms.model_number?.toLowerCase().includes(filter.toLowerCase()) ||
        ms.id.toLowerCase().includes(filter.toLowerCase()) ||
        ms.faction.toLowerCase().includes(filter.toLowerCase()))
  );

  const sorted = [...filtered].sort((a, b) => {
    let av: string | number;
    let bv: string | number;
    if (sortKey === "duplicate_credit_value") {
      av = a.blueprint.duplicate_credit_value;
      bv = b.blueprint.duplicate_credit_value;
    } else if (sortKey === "max_hp") {
      av = a.specs.max_hp;
      bv = b.specs.max_hp;
    } else if (sortKey === "armor") {
      av = a.specs.armor;
      bv = b.specs.armor;
    } else if (sortKey === "mobility") {
      av = a.specs.mobility;
      bv = b.specs.mobility;
    } else {
      av = a[sortKey] as string | number;
      bv = b[sortKey] as string | number;
    }
    if (av < bv) return sortDir === "asc" ? -1 : 1;
    if (av > bv) return sortDir === "asc" ? 1 : -1;
    return 0;
  });

  const thClass =
    "px-3 py-2 text-left text-xs font-bold uppercase tracking-wider cursor-pointer select-none text-[#ffb000]/80 hover:text-[#ffb000] whitespace-nowrap";
  const tdClass = "px-3 py-2 text-sm whitespace-nowrap";

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Filter by name / id / faction..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="flex-1 min-w-0 bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] placeholder-[#00ff41]/40 px-3 py-2 text-sm font-mono focus:outline-none focus:border-[#00ff41]"
        />
        <BlueprintFilterSelect value={blueprintFilter} onChange={setBlueprintFilter} />
      </div>
      <div className="overflow-x-auto border border-[#00ff41]/20">
        <table className="min-w-full text-[#00ff41] font-mono">
          <thead className="bg-[#0a0a0a] border-b border-[#00ff41]/20">
            <tr>
              <th className={thClass} onClick={() => handleSort("id")}>
                ID <SortIcon active={sortKey === "id"} dir={sortDir} />
              </th>
              <th className={thClass} onClick={() => handleSort("model_number")}>
                型番 <SortIcon active={sortKey === "model_number"} dir={sortDir} />
              </th>
              <th className={thClass} onClick={() => handleSort("name")}>
                名前 <SortIcon active={sortKey === "name"} dir={sortDir} />
              </th>
              <th className={thClass} onClick={() => handleSort("faction")}>
                勢力 <SortIcon active={sortKey === "faction"} dir={sortDir} />
              </th>
              <th className={thClass} onClick={() => handleSort("price")}>
                価格 <SortIcon active={sortKey === "price"} dir={sortDir} />
              </th>
              <th className={`${thClass} cursor-default`}>設計図</th>
              <th className={thClass} onClick={() => handleSort("duplicate_credit_value")}>
                換金額 <SortIcon active={sortKey === "duplicate_credit_value"} dir={sortDir} />
              </th>
              <th className={thClass} onClick={() => handleSort("max_hp")}>
                HP <SortIcon active={sortKey === "max_hp"} dir={sortDir} />
              </th>
              <th className={thClass} onClick={() => handleSort("armor")}>
                装甲 <SortIcon active={sortKey === "armor"} dir={sortDir} />
              </th>
              <th className={thClass} onClick={() => handleSort("mobility")}>
                機動性 <SortIcon active={sortKey === "mobility"} dir={sortDir} />
              </th>
              <th className={`${thClass} cursor-default`}>操作</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((ms) => {
              const isSelected = ms.id === selectedId;
              return (
                <tr
                  key={ms.id}
                  onClick={() => onSelect(ms)}
                  className={`cursor-pointer border-b border-[#00ff41]/10 transition-colors ${
                    isSelected
                      ? "bg-[#00ff41]/10 border-[#00ff41]/40"
                      : "hover:bg-[#00ff41]/5"
                  }`}
                >
                  <td className={`${tdClass} text-[#00ff41]/60`}>{ms.id}</td>
                  <td className={`${tdClass} text-[#00ff41]/60`}>{ms.model_number || "—"}</td>
                  <td className={`${tdClass} font-bold ${isSelected ? "text-[#ffb000]" : ""}`}>
                    {ms.name}
                  </td>
                  <td className={tdClass}>
                    <span
                      className={`px-2 py-0.5 text-xs font-bold ${
                        ms.faction === "FEDERATION"
                          ? "bg-blue-900/40 text-blue-300 border border-blue-700/40"
                          : ms.faction === "ZEON"
                          ? "bg-red-900/40 text-red-300 border border-red-700/40"
                          : "bg-[#333]/40 text-[#aaa] border border-[#555]/40"
                      }`}
                    >
                      {ms.faction || "—"}
                    </span>
                  </td>
                  <td className={tdClass}>{ms.price.toLocaleString()} C</td>
                  <td className={tdClass}>
                    <BlueprintBadge blueprint={ms.blueprint} />
                  </td>
                  <td className={tdClass}>{ms.blueprint.duplicate_credit_value.toLocaleString()} C</td>
                  <td className={tdClass}>{ms.specs.max_hp}</td>
                  <td className={tdClass}>{ms.specs.armor}</td>
                  <td className={tdClass}>{ms.specs.mobility.toFixed(2)}</td>
                  <td className={tdClass} onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => onDelete(ms)}
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
                <td colSpan={11} className="text-center text-[#00ff41]/40 py-8 text-sm">
                  機体データが見つかりません
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-[#00ff41]/40 text-right">
        {sorted.length} / {mobileSuits.length} 機体表示中
      </p>
    </div>
  );
}
