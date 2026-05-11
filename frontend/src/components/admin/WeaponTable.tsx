/* frontend/src/components/admin/WeaponTable.tsx */
"use client";

import { useState } from "react";
import { MasterWeapon } from "@/types/battle";

interface WeaponTableProps {
  weapons: MasterWeapon[];
  selectedId: string | null;
  onSelect: (weapon: MasterWeapon) => void;
  onDelete: (weapon: MasterWeapon) => void;
}

type SortKey = "id" | "name" | "price" | "type" | "power" | "range" | "accuracy";
type SortDir = "asc" | "desc";

export default function WeaponTable({
  weapons,
  selectedId,
  onSelect,
  onDelete,
}: WeaponTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("name");
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

  const filtered = weapons.filter(
    (w) =>
      w.name.toLowerCase().includes(filter.toLowerCase()) ||
      w.id.toLowerCase().includes(filter.toLowerCase()) ||
      (w.weapon.type ?? "").toLowerCase().includes(filter.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => {
    let av: string | number;
    let bv: string | number;
    if (sortKey === "power") {
      av = a.weapon.power;
      bv = b.weapon.power;
    } else if (sortKey === "range") {
      av = a.weapon.range;
      bv = b.weapon.range;
    } else if (sortKey === "accuracy") {
      av = a.weapon.accuracy;
      bv = b.weapon.accuracy;
    } else if (sortKey === "type") {
      av = a.weapon.type ?? "";
      bv = b.weapon.type ?? "";
    } else {
      av = a[sortKey] as string | number;
      bv = b[sortKey] as string | number;
    }
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

  return (
    <div className="space-y-3">
      <input
        type="text"
        placeholder="Filter by name / id / type..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] placeholder-[#00ff41]/40 px-3 py-2 text-sm font-mono focus:outline-none focus:border-[#00ff41]"
      />
      <div className="overflow-x-auto border border-[#00ff41]/20">
        <table className="min-w-full text-[#00ff41] font-mono">
          <thead className="bg-[#0a0a0a] border-b border-[#00ff41]/20">
            <tr>
              <th className={thClass} onClick={() => handleSort("name")}>
                名前 <SortIcon k="name" />
              </th>
              <th className={thClass} onClick={() => handleSort("price")}>
                価格 <SortIcon k="price" />
              </th>
              <th className={thClass} onClick={() => handleSort("type")}>
                種別 <SortIcon k="type" />
              </th>
              <th className={`${thClass} cursor-default`}>近接</th>
              <th className={thClass} onClick={() => handleSort("power")}>
                威力 <SortIcon k="power" />
              </th>
              <th className={thClass} onClick={() => handleSort("range")}>
                射程 <SortIcon k="range" />
              </th>
              <th className={thClass} onClick={() => handleSort("accuracy")}>
                命中 <SortIcon k="accuracy" />
              </th>
              <th className={`${thClass} cursor-default`}>操作</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((w) => {
              const isSelected = w.id === selectedId;
              return (
                <tr
                  key={w.id}
                  onClick={() => onSelect(w)}
                  className={`cursor-pointer border-b border-[#00ff41]/10 transition-colors ${
                    isSelected
                      ? "bg-[#00ff41]/10 border-[#00ff41]/40"
                      : "hover:bg-[#00ff41]/5"
                  }`}
                >
                  <td className={`${tdClass} font-bold ${isSelected ? "text-[#ffb000]" : ""}`}>
                    <div>{w.name}</div>
                    <div className="text-xs text-[#00ff41]/40 font-normal">{w.id}</div>
                  </td>
                  <td className={tdClass}>{w.price.toLocaleString()} C</td>
                  <td className={tdClass}>
                    <span
                      className={`px-2 py-0.5 text-xs font-bold ${
                        w.weapon.type === "BEAM"
                          ? "bg-blue-900/40 text-blue-300 border border-blue-700/40"
                          : "bg-orange-900/40 text-orange-300 border border-orange-700/40"
                      }`}
                    >
                      {w.weapon.type ?? "—"}
                    </span>
                  </td>
                  <td className={tdClass}>
                    {w.weapon.is_melee ? (
                      <span className="text-yellow-400 text-xs font-bold">MELEE</span>
                    ) : (
                      <span className="text-[#00ff41]/30 text-xs">—</span>
                    )}
                  </td>
                  <td className={tdClass}>{w.weapon.power}</td>
                  <td className={tdClass}>{w.weapon.range}</td>
                  <td className={tdClass}>{w.weapon.accuracy}%</td>
                  <td className={tdClass} onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={() => onDelete(w)}
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
                <td colSpan={8} className="text-center text-[#00ff41]/40 py-8 text-sm">
                  武器データが見つかりません
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-[#00ff41]/40 text-right">
        {sorted.length} / {weapons.length} 武器表示中
      </p>
    </div>
  );
}
