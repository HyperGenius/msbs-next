/* admin-tool/src/components/admin/NpcTable.tsx */
"use client";

import { useState } from "react";
import { NpcPersonality, NpcPilot } from "@/types/admin";

interface NpcTableProps {
  npcs: NpcPilot[];
  selectedId: string | null;
  onSelect: (npc: NpcPilot) => void;
}

type SortKey = "name" | "npc_personality" | "level" | "exp" | "credits" | "mobile_suit_count";
type SortDir = "asc" | "desc";

const PERSONALITY_OPTIONS: NpcPersonality[] = ["AGGRESSIVE", "CAUTIOUS", "SNIPER"];

export default function NpcTable({ npcs, selectedId, onSelect }: NpcTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("level");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [filter, setFilter] = useState("");
  const [personalityFilter, setPersonalityFilter] = useState<NpcPersonality | "">("");
  const [minLevel, setMinLevel] = useState("");
  const [maxLevel, setMaxLevel] = useState("");
  const [aceFilter, setAceFilter] = useState<"" | "ace" | "normal">("");

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const filtered = npcs.filter((npc) => {
    if (filter && !npc.name.toLowerCase().includes(filter.toLowerCase())) return false;
    if (personalityFilter && npc.npc_personality !== personalityFilter) return false;
    if (minLevel && npc.level < Number(minLevel)) return false;
    if (maxLevel && npc.level > Number(maxLevel)) return false;
    if (aceFilter === "ace" && !npc.is_ace) return false;
    if (aceFilter === "normal" && npc.is_ace) return false;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    const av = a[sortKey] ?? "";
    const bv = b[sortKey] ?? "";
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
  const selectClass =
    "bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-2 text-sm font-mono focus:outline-none focus:border-[#00ff41]";

  return (
    <div className="space-y-3">
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="text"
          placeholder="Filter by name..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="flex-1 bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] placeholder-[#00ff41]/40 px-3 py-2 text-sm font-mono focus:outline-none focus:border-[#00ff41]"
        />
        <select
          value={personalityFilter}
          onChange={(e) => setPersonalityFilter(e.target.value as NpcPersonality | "")}
          className={selectClass}
        >
          <option value="">性格: すべて</option>
          {PERSONALITY_OPTIONS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <select
          value={aceFilter}
          onChange={(e) => setAceFilter(e.target.value as "" | "ace" | "normal")}
          className={selectClass}
        >
          <option value="">エース: すべて</option>
          <option value="ace">エースのみ</option>
          <option value="normal">通常NPCのみ</option>
        </select>
        <input
          type="number"
          placeholder="Lv 下限"
          value={minLevel}
          onChange={(e) => setMinLevel(e.target.value)}
          className="w-24 bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] placeholder-[#00ff41]/40 px-2 py-2 text-sm font-mono focus:outline-none focus:border-[#00ff41]"
        />
        <input
          type="number"
          placeholder="Lv 上限"
          value={maxLevel}
          onChange={(e) => setMaxLevel(e.target.value)}
          className="w-24 bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] placeholder-[#00ff41]/40 px-2 py-2 text-sm font-mono focus:outline-none focus:border-[#00ff41]"
        />
      </div>
      <div className="overflow-x-auto border border-[#00ff41]/20">
        <table className="min-w-full text-[#00ff41] font-mono">
          <thead className="bg-[#0a0a0a] border-b border-[#00ff41]/20">
            <tr>
              <th className={thClass} onClick={() => handleSort("name")}>
                名前 <SortIcon k="name" />
              </th>
              <th className={thClass} onClick={() => handleSort("npc_personality")}>
                性格 <SortIcon k="npc_personality" />
              </th>
              <th className={thClass} onClick={() => handleSort("level")}>
                Lv <SortIcon k="level" />
              </th>
              <th className={thClass} onClick={() => handleSort("exp")}>
                EXP <SortIcon k="exp" />
              </th>
              <th className={thClass} onClick={() => handleSort("credits")}>
                クレジット <SortIcon k="credits" />
              </th>
              <th className={thClass} onClick={() => handleSort("mobile_suit_count")}>
                所属機体数 <SortIcon k="mobile_suit_count" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((npc) => {
              const isSelected = npc.id === selectedId;
              return (
                <tr
                  key={npc.id}
                  onClick={() => onSelect(npc)}
                  className={`cursor-pointer border-b border-[#00ff41]/10 transition-colors ${
                    isSelected ? "bg-[#00ff41]/10 border-[#00ff41]/40" : "hover:bg-[#00ff41]/5"
                  }`}
                >
                  <td className={`${tdClass} font-bold ${isSelected ? "text-[#ffb000]" : ""}`}>
                    {npc.name}
                    {npc.is_ace && (
                      <span className="ml-2 px-1.5 py-0.5 text-[10px] font-bold bg-[#ffb000]/20 text-[#ffb000] border border-[#ffb000]/50">
                        ACE
                      </span>
                    )}
                  </td>
                  <td className={tdClass}>{npc.npc_personality ?? "—"}</td>
                  <td className={tdClass}>{npc.level}</td>
                  <td className={tdClass}>{npc.exp.toLocaleString()}</td>
                  <td className={tdClass}>{npc.credits.toLocaleString()} C</td>
                  <td className={tdClass}>{npc.mobile_suit_count}</td>
                </tr>
              );
            })}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center text-[#00ff41]/40 py-8 text-sm">
                  NPCデータが見つかりません
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-[#00ff41]/40 text-right">
        {sorted.length} / {npcs.length} NPC表示中
      </p>
    </div>
  );
}
