"use client";

import { useState } from "react";
import { usePilot, useSkills } from "@/services/api";
import SciFiHeading from "@/components/ui/SciFiHeading";
import PilotDashboardHeader from "@/components/pilot/PilotDashboardHeader";
import RenamePilotModal from "@/components/pilot/RenamePilotModal";
import ParameterTuningModal from "@/components/pilot/ParameterTuningModal";
import SkillDevelopmentModal from "@/components/pilot/SkillDevelopmentModal";
import { STATUS_LABELS, getStatRank, STAT_RANK_COLORS } from "@/components/pilot/StatusStatCard";
import { StatKey } from "@/components/pilot/StatusRadarChart";

/** パラメータカードに表示するステータスの順序 */
const STAT_ORDER: StatKey[] = ["sht", "mel", "intel", "ref", "tou", "luk"];

export default function PilotPage() {
  const { pilot, isLoading: pilotLoading, mutate: mutatePilot } = usePilot();
  const { skills, isLoading: skillsLoading } = useSkills();

  const [isNameModalOpen, setIsNameModalOpen] = useState(false);
  const [isParamModalOpen, setIsParamModalOpen] = useState(false);
  const [isSkillModalOpen, setIsSkillModalOpen] = useState(false);

  if (pilotLoading || skillsLoading) {
    return (
      <div className="min-h-screen bg-[#050505] text-[#00ff41] p-8 font-mono">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-xl animate-pulse">LOADING...</p>
        </div>
      </div>
    );
  }

  if (!pilot) {
    return (
      <div className="min-h-screen bg-[#050505] text-[#00ff41] p-8 font-mono">
        <div className="max-w-4xl mx-auto">
          <p className="text-center text-xl text-red-400">Pilot not found</p>
        </div>
      </div>
    );
  }

  /** パイロットの各ステータス現在値 */
  const pilotStats: Record<StatKey, number> = {
    sht: pilot.sht,
    mel: pilot.mel,
    intel: pilot.intel,
    ref: pilot.ref,
    tou: pilot.tou,
    luk: pilot.luk,
  };

  /** 習得済みスキルの数 */
  const unlockedSkillCount = Object.values(pilot.skills).filter((lv) => lv > 0).length;

  return (
    <div className="min-h-screen bg-[#050505] text-gray-100 p-4 sm:p-6 md:p-8 font-mono">
      <div className="max-w-4xl mx-auto space-y-6">
        <SciFiHeading level={1} className="text-center">
          PILOT MANAGEMENT
        </SciFiHeading>

        {/* ── ダッシュボードヘッダー（常時表示） ── */}
        <PilotDashboardHeader
          pilot={pilot}
          onOpenNameModal={() => setIsNameModalOpen(true)}
        />

        {/* ── アクションカード（2列グリッド） ── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

          {/* パラメータカード */}
          <button
            onClick={() => setIsParamModalOpen(true)}
            className="text-left border border-[#ffb000]/40 bg-[#ffb000]/5 p-4 flex flex-col gap-3
              hover:border-[#ffb000]/80 hover:bg-[#ffb000]/10 transition-colors"
          >
            {/* カードヘッダー */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold tracking-widest text-[#ffb000] uppercase">
                ◈ Parameters
              </span>
              {pilot.status_points > 0 && (
                <span className="text-xs font-bold text-[#00ff41] drop-shadow-[0_0_4px_#00ff41]">
                  [{pilot.status_points} pt]
                </span>
              )}
            </div>

            {/* ミニステータスグリッド */}
            <div className="grid grid-cols-3 gap-x-3 gap-y-1">
              {STAT_ORDER.map((stat) => {
                const val = pilotStats[stat];
                const rank = getStatRank(val);
                const color = STAT_RANK_COLORS[rank];
                return (
                  <div key={stat} className="flex items-center gap-1">
                    <span className="text-[10px] text-gray-500 w-7">{STATUS_LABELS[stat].abbr}</span>
                    <span className="text-xs font-bold" style={{ color }}>{rank}</span>
                  </div>
                );
              })}
            </div>

            {/* タップ促進テキスト */}
            <div className="flex items-center justify-end gap-1 text-[#ffb000]/60 text-[10px] font-bold tracking-widest">
              TUNE PARAMETERS ▶
            </div>
          </button>

          {/* スキルカード */}
          <button
            onClick={() => setIsSkillModalOpen(true)}
            className="text-left border border-[#00f0ff]/40 bg-[#00f0ff]/5 p-4 flex flex-col gap-3
              hover:border-[#00f0ff]/80 hover:bg-[#00f0ff]/10 transition-colors"
          >
            {/* カードヘッダー */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold tracking-widest text-[#00f0ff] uppercase">
                ◈ Skills
              </span>
              {pilot.skill_points > 0 && (
                <span className="text-xs font-bold text-[#00f0ff] drop-shadow-[0_0_4px_#00f0ff]">
                  [{pilot.skill_points} SP]
                </span>
              )}
            </div>

            {/* スキルサマリー */}
            <div className="space-y-1">
              <p className="text-sm text-gray-300">
                習得スキル:{" "}
                <span className="font-bold text-[#00f0ff]">{unlockedSkillCount}</span>
                <span className="text-gray-500"> / {(skills ?? []).length}</span>
              </p>
              {pilot.skill_points > 0 && (
                <p className="text-xs text-[#00ff41]">
                  ▸ {pilot.skill_points} SP を割り振れます
                </p>
              )}
            </div>

            {/* タップ促進テキスト */}
            <div className="flex items-center justify-end gap-1 text-[#00f0ff]/60 text-[10px] font-bold tracking-widest">
              DEVELOP SKILLS ▶
            </div>
          </button>
        </div>
      </div>

      {/* ── モーダル群 ── */}
      {isNameModalOpen && (
        <RenamePilotModal
          pilot={pilot}
          onClose={() => setIsNameModalOpen(false)}
          mutatePilot={mutatePilot}
        />
      )}

      {isParamModalOpen && (
        <ParameterTuningModal
          pilot={pilot}
          mutatePilot={mutatePilot}
          onClose={() => setIsParamModalOpen(false)}
        />
      )}

      {isSkillModalOpen && (
        <SkillDevelopmentModal
          pilot={pilot}
          skills={skills ?? []}
          mutatePilot={mutatePilot}
          onClose={() => setIsSkillModalOpen(false)}
        />
      )}
    </div>
  );
}
