/* frontend/src/components/history/BattleSummaryPanel.tsx */
"use client";

import { BattleLog, BattleResult, MobileSuit } from "@/types/battle";
import { usePartHitSummary } from "@/hooks/usePartHitSummary";
import { useWeaponAccuracySummary } from "@/hooks/useWeaponAccuracySummary";
import { useDetectionSummary } from "@/hooks/useDetectionSummary";
import PartHitSummaryTable from "./PartHitSummaryTable";

interface StatCardProps {
  label: string;
  value: string;
  unit?: string;
  colorClass: string;
}

function StatCard({ label, value, unit, colorClass }: StatCardProps) {
  return (
    <div className="flex-1 bg-gray-900 border border-gray-700 rounded px-3 py-2">
      <div className="text-[10px] text-gray-500">{label}</div>
      <div className={`text-lg font-bold ${colorClass}`}>
        {value}
        {unit && <span className="text-xs text-gray-500 font-normal ml-0.5">{unit}</span>}
      </div>
    </div>
  );
}

interface BattleSummaryPanelProps {
  battle: BattleResult;
  logs: BattleLog[];
  playerId: string | null;
  enemies: MobileSuit[];
}

/**
 * バトルヒストリー詳細モーダルの戦果サマリー（Issue #521）。
 * タブ切り替えは行わず常時表示する。ここは「自身のカスタマイズの妥当性を判断する」ための
 * 分析用途なので、チャプタートラック/3D演出とは異なり実数値をそのまま表示する。
 */
export default function BattleSummaryPanel({ battle, logs, playerId, enemies }: BattleSummaryPanelProps) {
  const partHitSummary = usePartHitSummary(battle, logs, playerId);
  const equippedWeaponNames = battle.player_info?.weapons?.map((w) => w.name) ?? [];
  const weaponAccuracy = useWeaponAccuracySummary(logs, playerId, equippedWeaponNames);
  const detection = useDetectionSummary(logs, playerId, enemies);

  return (
    <div className="pt-3">
      <div className="flex gap-2 mb-4">
        <StatCard
          label="撃墜"
          value={battle.kills != null ? String(battle.kills) : "—"}
          unit="機"
          colorClass="text-green-400"
        />
        <StatCard
          label="被攻撃回数"
          value={battle.attacks_received_count != null ? String(battle.attacks_received_count) : "—"}
          unit="回"
          colorClass="text-red-400"
        />
        <StatCard label="索敵成功" value={String(detection.captured)} unit={`/ ${detection.total}機`} colorClass="text-cyan-400" />
      </div>

      {weaponAccuracy.length > 0 && (
        <div className="mb-4">
          <h4 className="text-xs font-semibold text-gray-400 mb-1">命中率</h4>
          <div className="flex flex-col gap-1.5">
            {weaponAccuracy.map((w) => (
              <div key={w.weaponName} className="flex items-center gap-2 text-xs">
                <span className="w-28 flex-none text-gray-200 truncate">{w.weaponName}</span>
                <div className="flex-1 h-1.5 bg-gray-900 rounded overflow-hidden">
                  <div
                    className="h-full bg-green-500"
                    style={{ width: `${(w.accuracy ?? 0) * 100}%` }}
                  />
                </div>
                <span className="w-24 flex-none text-right text-gray-400">
                  {w.hits}/{w.attempts} ({w.accuracy != null ? `${Math.round(w.accuracy * 100)}%` : "--%"})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <PartHitSummaryTable summary={partHitSummary} />
    </div>
  );
}
