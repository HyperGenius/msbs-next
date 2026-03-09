"use client";

import { useState } from "react";
import { usePilot, useSkills } from "@/services/api";
import SciFiHeading from "@/components/ui/SciFiHeading";
import PilotDashboardHeader from "@/components/pilot/PilotDashboardHeader";
import RenamePilotModal from "@/components/pilot/RenamePilotModal";
import ParameterTuningPanel from "@/components/pilot/ParameterTuningPanel";
import SkillDevelopmentPanel from "@/components/pilot/SkillDevelopmentPanel";

type ActiveTab = "parameters" | "skills";

export default function PilotPage() {
  const { pilot, isLoading: pilotLoading, mutate: mutatePilot } = usePilot();
  const { skills, isLoading: skillsLoading } = useSkills();

  const [activeTab, setActiveTab] = useState<ActiveTab>("parameters");
  const [isNameModalOpen, setIsNameModalOpen] = useState(false);

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

        {/* ── タブナビゲーション ── */}
        <div className="flex border-b border-gray-700">
          <button
            onClick={() => setActiveTab("parameters")}
            className={`px-6 py-3 text-sm font-bold uppercase tracking-widest transition-colors border-b-2 -mb-px ${
              activeTab === "parameters"
                ? "border-[#ffb000] text-[#ffb000]"
                : "border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500"
            }`}
          >
            ◈ Parameters
            {pilot.status_points > 0 && (
              <span className="ml-2 text-xs text-[#00ff41] drop-shadow-[0_0_4px_#00ff41]">
                [{pilot.status_points}]
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab("skills")}
            className={`px-6 py-3 text-sm font-bold uppercase tracking-widest transition-colors border-b-2 -mb-px ${
              activeTab === "skills"
                ? "border-[#00f0ff] text-[#00f0ff]"
                : "border-transparent text-gray-400 hover:text-gray-200 hover:border-gray-500"
            }`}
          >
            ◈ Skills
            {pilot.skill_points > 0 && (
              <span className="ml-2 text-xs text-[#00f0ff] drop-shadow-[0_0_4px_#00f0ff]">
                [{pilot.skill_points} SP]
              </span>
            )}
          </button>
        </div>

        {/* ── タブコンテンツ ── */}
        <div className="animate-in fade-in duration-200">
          {activeTab === "parameters" && (
            <ParameterTuningPanel pilot={pilot} mutatePilot={mutatePilot} />
          )}
          {activeTab === "skills" && (
            <SkillDevelopmentPanel
              pilot={pilot}
              skills={skills ?? []}
              mutatePilot={mutatePilot}
            />
          )}
        </div>
      </div>

      {/* ── 名前変更モーダル ── */}
      {isNameModalOpen && (
        <RenamePilotModal
          pilot={pilot}
          onClose={() => setIsNameModalOpen(false)}
          mutatePilot={mutatePilot}
        />
      )}
    </div>
  );
}
