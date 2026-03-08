"use client";

import { useState } from "react";
import { Pilot, SkillDefinition } from "@/types/battle";
import { unlockSkill } from "@/services/api";
import { KeyedMutator } from "swr";
import SciFiPanel from "@/components/ui/SciFiPanel";
import SciFiCard from "@/components/ui/SciFiCard";
import HoldSciFiButton from "@/components/ui/HoldSciFiButton";

interface SkillDevelopmentPanelProps {
  pilot: Pilot;
  skills: SkillDefinition[];
  mutatePilot: KeyedMutator<Pilot>;
}

export default function SkillDevelopmentPanel({ pilot, skills, mutatePilot }: SkillDevelopmentPanelProps) {
  const [unlocking, setUnlocking] = useState<string | null>(null);
  const [skillError, setSkillError] = useState<string>("");
  const [skillSuccess, setSkillSuccess] = useState<string>("");

  const handleUnlockSkill = async (skillId: string) => {
    setUnlocking(skillId);
    setSkillError("");
    setSkillSuccess("");
    try {
      const response = await unlockSkill(skillId);
      setSkillSuccess(response.message);
      await mutatePilot();
    } catch (err) {
      setSkillError(err instanceof Error ? err.message : "スキルのアンロックに失敗しました");
    } finally {
      setUnlocking(null);
    }
  };

  return (
    <SciFiPanel variant="accent" className="p-6">
      <div className="flex items-center justify-between mb-5 border-b border-[#00f0ff]/30 pb-3">
        <h2 className="text-sm font-bold tracking-widest text-[#00f0ff] uppercase">
          SKILL DEVELOPMENT
        </h2>
      </div>

      {skillError && (
        <div className="border border-red-500 bg-red-900/20 p-3 mb-4">
          <p className="text-red-400 text-sm">{skillError}</p>
        </div>
      )}
      {skillSuccess && (
        <div className="border border-[#00ff41] bg-[#00ff41]/10 p-3 mb-4">
          <p className="text-[#00ff41] text-sm">{skillSuccess}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {skills.map((skill) => {
          const currentLevel = pilot.skills[skill.id] || 0;
          const isMaxLevel = currentLevel >= skill.max_level;
          const canUpgrade = pilot.skill_points > 0 && !isMaxLevel;
          const isUnlocking = unlocking === skill.id;

          return (
            <SciFiCard key={skill.id} variant="accent" className="flex flex-col gap-3">
              <div className="flex justify-between items-start">
                <div className="flex-1 min-w-0 pr-2">
                  <h3 className="text-sm font-bold text-[#00f0ff]">{skill.name}</h3>
                  <p className="text-xs text-gray-300 mt-0.5 leading-snug">{skill.description}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-xs text-gray-400">Lv</p>
                  <p className="text-lg font-bold text-[#ffb000]">
                    {currentLevel}<span className="text-xs text-gray-500">/{skill.max_level}</span>
                  </p>
                </div>
              </div>

              <div className="text-xs text-gray-300">
                <span>効果: </span>
                <span className="text-[#00f0ff] font-bold">+{skill.effect_per_level}% / Lv</span>
                {currentLevel > 0 && (
                  <span className="ml-2 text-[#ffb000]">
                    (現在: +{(currentLevel * skill.effect_per_level).toFixed(1)}%)
                  </span>
                )}
              </div>

              {isMaxLevel ? (
                <div className="text-center py-2 border border-[#00f0ff]/30 text-xs text-gray-400 font-bold">
                  最大レベル
                </div>
              ) : pilot.skill_points === 0 ? (
                <div className="text-center py-2 border border-[#ffb000]/30 text-xs text-gray-400 font-bold">
                  SP不足
                </div>
              ) : (
                <HoldSciFiButton
                  onHoldComplete={() => handleUnlockSkill(skill.id)}
                  disabled={!canUpgrade}
                  loading={isUnlocking}
                  label={`強化 (-1 SP)`}
                  loadingLabel="強化中..."
                />
              )}
            </SciFiCard>
          );
        })}
      </div>
    </SciFiPanel>
  );
}
