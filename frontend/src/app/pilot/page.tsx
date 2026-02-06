"use client";

import { useState } from "react";
import { usePilot, useSkills, unlockSkill } from "@/services/api";
import { SkillDefinition } from "@/types/battle";

export default function PilotPage() {
  const { pilot, isLoading: pilotLoading, mutate: mutatePilot } = usePilot();
  const { skills, isLoading: skillsLoading } = useSkills();
  const [unlocking, setUnlocking] = useState<string | null>(null);
  const [error, setError] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const handleUnlockSkill = async (skillId: string) => {
    if (!pilot) return;
    
    setUnlocking(skillId);
    setError("");
    setSuccessMessage("");
    
    try {
      const response = await unlockSkill(skillId);
      setSuccessMessage(response.message);
      // Refresh pilot data
      await mutatePilot();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unlock skill");
    } finally {
      setUnlocking(null);
    }
  };

  if (pilotLoading || skillsLoading) {
    return (
      <div className="min-h-screen bg-gray-900 text-green-400 p-8">
        <div className="max-w-7xl mx-auto">
          <p className="text-center text-xl">Loading...</p>
        </div>
      </div>
    );
  }

  if (!pilot) {
    return (
      <div className="min-h-screen bg-gray-900 text-green-400 p-8">
        <div className="max-w-7xl mx-auto">
          <p className="text-center text-xl text-red-400">Pilot not found</p>
        </div>
      </div>
    );
  }

  const requiredExp = pilot.level * 100;
  const expProgress = (pilot.exp / requiredExp) * 100;

  return (
    <div className="min-h-screen bg-gray-900 text-green-400 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-center">Pilot Skills</h1>

        {/* Pilot Status */}
        <div className="bg-gray-800 border border-green-700 rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-bold mb-4">{pilot.name}</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-gray-400 text-sm">Level</p>
              <p className="text-2xl font-bold text-yellow-400">{pilot.level}</p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Experience</p>
              <p className="text-lg">
                <span className="font-bold">{pilot.exp}</span>
                <span className="text-sm text-gray-400"> / {requiredExp}</span>
              </p>
              <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${expProgress}%` }}
                />
              </div>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Credits</p>
              <p className="text-2xl font-bold text-green-400">{pilot.credits.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-gray-400 text-sm">Skill Points</p>
              <p className="text-2xl font-bold text-purple-400">{pilot.skill_points}</p>
            </div>
          </div>
        </div>

        {/* Messages */}
        {error && (
          <div className="bg-red-900/30 border border-red-500 rounded-lg p-4 mb-4">
            <p className="text-red-400">{error}</p>
          </div>
        )}
        {successMessage && (
          <div className="bg-green-900/30 border border-green-500 rounded-lg p-4 mb-4">
            <p className="text-green-400">{successMessage}</p>
          </div>
        )}

        {/* Skills */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {skills?.map((skill: SkillDefinition) => {
            const currentLevel = pilot.skills[skill.id] || 0;
            const isMaxLevel = currentLevel >= skill.max_level;
            const canUpgrade = pilot.skill_points > 0 && !isMaxLevel;
            const isUnlocking = unlocking === skill.id;

            return (
              <div
                key={skill.id}
                className="bg-gray-800 border border-green-700 rounded-lg p-6 hover:border-green-500 transition-colors"
              >
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="text-xl font-bold text-green-400">{skill.name}</h3>
                    <p className="text-gray-400 text-sm mt-1">{skill.description}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-gray-400">Level</p>
                    <p className="text-2xl font-bold text-yellow-400">
                      {currentLevel} / {skill.max_level}
                    </p>
                  </div>
                </div>

                <div className="mb-4">
                  <p className="text-sm text-gray-300">
                    効果: <span className="text-blue-400 font-bold">+{skill.effect_per_level}%</span> / Level
                  </p>
                  {currentLevel > 0 && (
                    <p className="text-sm text-gray-300 mt-1">
                      現在の効果: <span className="text-purple-400 font-bold">+{(currentLevel * skill.effect_per_level).toFixed(1)}%</span>
                    </p>
                  )}
                </div>

                <button
                  onClick={() => handleUnlockSkill(skill.id)}
                  disabled={!canUpgrade || isUnlocking}
                  className={`w-full py-3 px-6 rounded font-bold transition-all ${
                    canUpgrade && !isUnlocking
                      ? "bg-purple-900 hover:bg-purple-800 text-white shadow-lg hover:shadow-purple-500/50"
                      : "bg-gray-700 text-gray-500 cursor-not-allowed"
                  }`}
                >
                  {isUnlocking ? (
                    "強化中..."
                  ) : isMaxLevel ? (
                    "最大レベル"
                  ) : pilot.skill_points === 0 ? (
                    "SP不足"
                  ) : (
                    "強化 (-1 SP)"
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
