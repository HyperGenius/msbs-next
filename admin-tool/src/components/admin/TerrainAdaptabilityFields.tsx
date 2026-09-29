"use client";

import { useAdminEnvironments } from "@/hooks/useAdminEnvironments";
import { TERRAIN_GRADES, TerrainGradeInput, setTerrainGrade, unmanagedTerrainKeys } from "@/lib/theater";

// MobileSuitSpecFields は MobileSuitEditForm を import するため、循環しないようここで定義する。
const inputCls =
  "w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-2 py-1 text-sm font-mono focus:outline-none focus:border-[#00ff41]";

interface TerrainAdaptabilityFieldsProps {
  /** 環境タイプID → ランク。キーが無い環境は環境タイプの既定ランク */
  value: Record<string, string>;
  onChange: (value: Record<string, string>) => void;
  error?: string;
}

/** 機体の地形適正を、環境タイプのマスターごとに選ぶ入力欄 */
export default function TerrainAdaptabilityFields({ value, onChange, error }: TerrainAdaptabilityFieldsProps) {
  const { environments, isLoading, isError } = useAdminEnvironments();

  if (isLoading) {
    return <p className="text-xs text-[#ffb000] animate-pulse">読み込み中...</p>;
  }
  if (isError || !environments) {
    return <p className="text-xs text-red-400">環境タイプを取得できません</p>;
  }

  const unmanaged = unmanagedTerrainKeys(environments, value);

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {environments.map((environment) => (
          <div key={environment.id}>
            <label className="block text-xs text-[#ffb000]/80 mb-0.5">
              {environment.name} ({environment.id})
            </label>
            <select
              value={value[environment.id] ?? ""}
              onChange={(e) => onChange(setTerrainGrade(value, environment.id, e.target.value as TerrainGradeInput))}
              className={inputCls}
            >
              <option value="">既定（{environment.default_terrain_grade}）</option>
              {TERRAIN_GRADES.map((grade) => (
                <option key={grade} value={grade}>
                  {grade}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
      <p className="text-xs text-[#00ff41]/40">
        「既定」はキーを保存せず、環境タイプの既定ランクを使う（環境タイプの既定ランクを変えると追従する）。
      </p>
      {unmanaged.length > 0 && (
        <p className="text-xs text-[#00ff41]/40">
          環境タイプのマスターに無い設定（{unmanaged.map((key) => `${key}: ${value[key]}`).join(" / ")}）は、そのまま保存する。
        </p>
      )}
    </div>
  );
}
