"use client";

import { MasterTechnology } from "@/types/admin";
import { formatThresholds, maxLevelOf } from "@/lib/technology";

interface TechnologyTableProps {
  technologies: MasterTechnology[];
  selectedId: string | null;
  onSelect: (tech: MasterTechnology) => void;
  onDelete: (tech: MasterTechnology) => void;
}

const thClass = "px-2 py-1 text-left text-[#ffb000]/80 font-normal";
const tdClass = "px-2 py-1.5";

/** 技術マスターの一覧。行を押すと編集対象にする */
export default function TechnologyTable({ technologies, selectedId, onSelect, onDelete }: TechnologyTableProps) {
  if (technologies.length === 0) {
    return <p className="py-6 text-center text-xs text-[#00ff41]/40">技術マスターが無い</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-[#00ff41]/30">
            <th className={thClass}>技術</th>
            <th className={thClass}>閾値（累計断片数）</th>
            <th className={`${thClass} text-right`}>最大Lv後の換金額</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {technologies.map((tech) => (
            <tr
              key={tech.id}
              onClick={() => onSelect(tech)}
              className={`border-b border-[#00ff41]/10 cursor-pointer hover:bg-[#00ff41]/5 ${
                tech.id === selectedId ? "bg-[#00ff41]/10" : ""
              }`}
            >
              <td className={tdClass}>
                <p className="font-bold">{tech.name}</p>
                <p className="text-[10px] text-[#00ff41]/40">{tech.id}</p>
              </td>
              <td className={tdClass}>
                {formatThresholds(tech.level_thresholds)}
                <span className="ml-1 text-[#00ff41]/40">（最大Lv{maxLevelOf(tech)}）</span>
              </td>
              <td className={`${tdClass} text-right`}>{tech.overflow_credit_value.toLocaleString()} C</td>
              <td className={tdClass}>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(tech);
                  }}
                  className="text-xs text-red-400 border border-red-500/40 px-2 py-0.5 hover:border-red-500"
                >
                  削除
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
