/* frontend/src/app/garage/components/SpecsDisplay.tsx */
"use client";

import { MobileSuit } from "@/types/battle";

interface SpecsDisplayProps {
  selectedMs: MobileSuit;
}

const TERRAIN_LIST = [
  { env: "SPACE", label: "宇宙", icon: "🌌" },
  { env: "GROUND", label: "地上", icon: "🏔️" },
  { env: "COLONY", label: "コロニー", icon: "🏢" },
  { env: "UNDERWATER", label: "水中", icon: "🌊" },
] as const;

function getRankColor(r: string): string {
  switch (r) {
    case "S": return "text-green-400";
    case "A": return "text-blue-400";
    case "B": return "text-yellow-400";
    case "C": return "text-orange-400";
    case "D": return "text-red-400";
    default: return "text-gray-400";
  }
}

function getRankModifier(r: string): string {
  switch (r) {
    case "S": return "+20%";
    case "A": return "±0%";
    case "B": return "-20%";
    case "C": return "-40%";
    case "D": return "-60%";
    default: return "±0%";
  }
}

export default function SpecsDisplay({ selectedMs }: SpecsDisplayProps) {
  return (
    <div className="pt-4 border-t border-green-800">
      <h3 className="text-lg font-bold mb-4 text-green-300">
        機体スペック (詳細)
      </h3>

      {/* Combat Aptitude */}
      <div className="mb-4 p-3 bg-gray-900 rounded">
        <h4 className="text-sm font-bold mb-2 text-red-400">
          戦闘適性
        </h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-400">格闘適性:</span>
            <span className="ml-2 font-bold text-red-400">
              ×{(selectedMs.melee_aptitude ?? 1.0).toFixed(1)}
            </span>
          </div>
          <div>
            <span className="text-gray-400">射撃適性:</span>
            <span className="ml-2 font-bold text-blue-400">
              ×{(selectedMs.shooting_aptitude ?? 1.0).toFixed(1)}
            </span>
          </div>
          <div>
            <span className="text-gray-400">命中補正:</span>
            <span className="ml-2 font-bold text-green-400">
              {(selectedMs.accuracy_bonus ?? 0.0) >= 0 ? "+" : ""}{(selectedMs.accuracy_bonus ?? 0.0).toFixed(1)}%
            </span>
          </div>
          <div>
            <span className="text-gray-400">回避補正:</span>
            <span className="ml-2 font-bold text-yellow-400">
              {(selectedMs.evasion_bonus ?? 0.0) >= 0 ? "+" : ""}{(selectedMs.evasion_bonus ?? 0.0).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Mobility Detail */}
      <div className="mb-4 p-3 bg-gray-900 rounded">
        <h4 className="text-sm font-bold mb-2 text-purple-400">
          機動性詳細
        </h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-400">加速性能:</span>
            <span className="ml-2 font-bold text-purple-400">
              ×{(selectedMs.acceleration_bonus ?? 1.0).toFixed(1)}
            </span>
          </div>
          <div>
            <span className="text-gray-400">旋回性能:</span>
            <span className="ml-2 font-bold text-purple-400">
              ×{(selectedMs.turning_bonus ?? 1.0).toFixed(1)}
            </span>
          </div>
        </div>
      </div>

      {/* Energy & Propellant */}
      <div className="mb-4 p-3 bg-gray-900 rounded">
        <h4 className="text-sm font-bold mb-2 text-cyan-400">
          エネルギー・推進剤
        </h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-400">最大EN:</span>
            <span className="ml-2 font-bold text-cyan-400">
              {selectedMs.max_en || 1000}
            </span>
          </div>
          <div>
            <span className="text-gray-400">EN回復:</span>
            <span className="ml-2 font-bold text-cyan-400">
              {selectedMs.en_recovery || 100}/ターン
            </span>
          </div>
          <div>
            <span className="text-gray-400">最大推進剤:</span>
            <span className="ml-2 font-bold text-purple-400">
              {selectedMs.max_propellant || 1000}
            </span>
          </div>
        </div>
      </div>

      {/* Resistance */}
      <div className="mb-4 p-3 bg-gray-900 rounded">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-400">対ビーム防御:</span>
            <span className="ml-2 font-bold text-blue-400">
              {((selectedMs.beam_resistance || 0) * 100).toFixed(0)}%
            </span>
          </div>
          <div>
            <span className="text-gray-400">対実弾防御:</span>
            <span className="ml-2 font-bold text-yellow-400">
              {((selectedMs.physical_resistance || 0) * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Terrain Adaptability */}
      <div className="mb-4 p-3 bg-gray-900 rounded border border-green-800">
        <h4 className="text-sm font-bold mb-2 text-green-400">地形適正</h4>
        <div className="grid grid-cols-4 gap-2 text-xs">
          {TERRAIN_LIST.map(({ env, label, icon }) => {
            const rank = selectedMs.terrain_adaptability?.[env] || "A";
            return (
              <div key={env} className="p-2 bg-gray-800 rounded text-center">
                <div className="text-base mb-1">{icon}</div>
                <div className="text-xs text-gray-400 mb-1">{label}</div>
                <div className={`text-lg font-bold ${getRankColor(rank)}`}>
                  {rank}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {getRankModifier(rank)}
                </div>
              </div>
            );
          })}
        </div>
        <p className="text-xs text-green-600 mt-2 opacity-70">
          地形適正により移動速度が変化します
        </p>
      </div>
    </div>
  );
}
