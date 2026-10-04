"use client";

import { MasterEnvironment } from "@/types/admin";

interface EnvironmentTableProps {
  environments: MasterEnvironment[];
  selectedId: string | null;
  onSelect: (environment: MasterEnvironment) => void;
  onDelete: (environment: MasterEnvironment) => void;
}

const thClass = "px-2 py-1 text-left text-[#ffb000]/80 font-normal";
const tdClass = "px-2 py-1.5";

/** 環境タイプの一覧。行を押すと編集対象にする */
export default function EnvironmentTable({ environments, selectedId, onSelect, onDelete }: EnvironmentTableProps) {
  if (environments.length === 0) {
    return <p className="py-6 text-center text-xs text-[#00ff41]/40">環境タイプが無い</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-[#00ff41]/30">
            <th className={thClass}>環境タイプ</th>
            <th className={`${thClass} text-right`}>索敵倍率</th>
            <th className={`${thClass} text-right`}>射撃ペナルティ</th>
            <th className={thClass}>障害物</th>
            <th className={thClass}>既定ランク</th>
            <th className={thClass}>描画</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {environments.map((environment) => (
            <tr
              key={environment.id}
              onClick={() => onSelect(environment)}
              className={`border-b border-[#00ff41]/10 cursor-pointer hover:bg-[#00ff41]/5 ${
                environment.id === selectedId ? "bg-[#00ff41]/10" : ""
              }`}
            >
              <td className={tdClass}>
                <p className="font-bold">{environment.name}</p>
                <p className="text-[10px] text-[#00ff41]/40">{environment.id}</p>
              </td>
              <td className={`${tdClass} text-right`}>×{environment.sensor_range_multiplier}</td>
              <td className={`${tdClass} text-right`}>
                {environment.ranged_accuracy_penalty}
                <span className="ml-1 text-[#00ff41]/40">（{environment.ranged_penalty_ref_distance}m）</span>
              </td>
              <td className={tdClass}>{environment.default_obstacle_density}</td>
              <td className={tdClass}>{environment.default_terrain_grade}</td>
              <td className={tdClass}>{environment.viewer_preset}</td>
              <td className={tdClass}>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(environment);
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
