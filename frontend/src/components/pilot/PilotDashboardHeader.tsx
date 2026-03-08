"use client";

import { Pilot } from "@/types/battle";
import SciFiPanel from "@/components/ui/SciFiPanel";

interface PilotDashboardHeaderProps {
  pilot: Pilot;
  onOpenNameModal: () => void;
}

export default function PilotDashboardHeader({ pilot, onOpenNameModal }: PilotDashboardHeaderProps) {
  const requiredExp = pilot.level * 100;
  const expProgress = Math.min((pilot.exp / requiredExp) * 100, 100);

  return (
    <SciFiPanel variant="secondary" className="p-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* 左: パイロット名 + RENAMEボタン */}
        <div className="flex items-center gap-4">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-widest mb-0.5">Pilot</p>
            <p className="text-2xl font-bold text-[#00ff41]">🏷️ {pilot.name}</p>
          </div>
          <button
            onClick={onOpenNameModal}
            className="px-3 py-1 border border-[#00ff41]/50 text-[#00ff41] text-xs font-bold
              hover:border-[#00ff41] hover:bg-[#00ff41]/10 transition-colors"
          >
            RENAME
          </button>
        </div>

        {/* 右: ステータスグリッド */}
        <div className="flex flex-wrap gap-4 sm:gap-6">
          <div className="text-center">
            <p className="text-xs text-gray-400 uppercase tracking-widest">Level</p>
            <p className="text-2xl font-bold text-[#ffb000]">{pilot.level}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-400 uppercase tracking-widest">Credits</p>
            <p className="text-lg font-bold text-[#ffb000]">{pilot.credits.toLocaleString()} CR</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-400 uppercase tracking-widest">Status Pts</p>
            <p className={`text-2xl font-bold ${pilot.status_points > 0 ? "text-[#00ff41] drop-shadow-[0_0_6px_#00ff41]" : "text-gray-500"}`}>
              {pilot.status_points} PT
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-400 uppercase tracking-widest">Skill Pts</p>
            <p className={`text-2xl font-bold ${pilot.skill_points > 0 ? "text-[#00f0ff] drop-shadow-[0_0_6px_#00f0ff]" : "text-gray-500"}`}>
              {pilot.skill_points} SP
            </p>
          </div>
        </div>
      </div>

      {/* EXPバー */}
      <div className="mt-4">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>EXP</span>
          <span>{pilot.exp} / {requiredExp}</span>
        </div>
        <div className="w-full bg-[#1a1a1a] h-2.5 border border-[#ffb000]/30">
          <div
            className="h-full bg-[#ffb000] transition-all duration-500"
            style={{ width: `${expProgress}%` }}
          />
        </div>
      </div>
    </SciFiPanel>
  );
}
