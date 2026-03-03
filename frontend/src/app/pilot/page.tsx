"use client";

import { useState } from "react";
import { usePilot, useSkills, unlockSkill, updatePilotName } from "@/services/api";
import { SkillDefinition } from "@/types/battle";
import SciFiPanel from "@/components/ui/SciFiPanel";
import SciFiCard from "@/components/ui/SciFiCard";
import SciFiInput from "@/components/ui/SciFiInput";
import SciFiButton from "@/components/ui/SciFiButton";
import SciFiHeading from "@/components/ui/SciFiHeading";
import HoldSciFiButton from "@/components/ui/HoldSciFiButton";

type ViewMode = "list" | "tree";

export default function PilotPage() {
  const { pilot, isLoading: pilotLoading, mutate: mutatePilot } = usePilot();
  const { skills, isLoading: skillsLoading } = useSkills();

  const [unlocking, setUnlocking] = useState<string | null>(null);
  const [error, setError] = useState<string>("");
  const [successMessage, setSuccessMessage] = useState<string>("");

  const [nameInput, setNameInput] = useState<string>("");
  const [nameError, setNameError] = useState<string>("");
  const [nameSuccess, setNameSuccess] = useState<string>("");
  const [nameUpdating, setNameUpdating] = useState<boolean>(false);

  const [viewMode, setViewMode] = useState<ViewMode>("list");

  const handleUnlockSkill = async (skillId: string) => {
    if (!pilot) return;
    setUnlocking(skillId);
    setError("");
    setSuccessMessage("");
    try {
      const response = await unlockSkill(skillId);
      setSuccessMessage(response.message);
      await mutatePilot();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unlock skill");
    } finally {
      setUnlocking(null);
    }
  };

  const handleUpdateName = async () => {
    if (!pilot) return;
    setNameError("");
    setNameSuccess("");
    const trimmed = nameInput.trim();
    if (!trimmed) {
      setNameError("パイロット名を入力してください");
      return;
    }
    setNameUpdating(true);
    try {
      await updatePilotName(trimmed);
      setNameSuccess("パイロット名を更新しました");
      setNameInput("");
      await mutatePilot();
    } catch (err) {
      setNameError(err instanceof Error ? err.message : "名前の更新に失敗しました");
    } finally {
      setNameUpdating(false);
    }
  };

  if (pilotLoading || skillsLoading) {
    return (
      <div className="min-h-screen bg-[#050505] text-[#00ff41] p-8 font-mono">
        <div className="max-w-7xl mx-auto">
          <p className="text-center text-xl animate-pulse">LOADING...</p>
        </div>
      </div>
    );
  }

  if (!pilot) {
    return (
      <div className="min-h-screen bg-[#050505] text-[#00ff41] p-8 font-mono">
        <div className="max-w-7xl mx-auto">
          <p className="text-center text-xl text-red-400">Pilot not found</p>
        </div>
      </div>
    );
  }

  const requiredExp = pilot.level * 100;
  const expProgress = Math.min((pilot.exp / requiredExp) * 100, 100);

  return (
    <div className="min-h-screen bg-[#050505] text-[#00ff41] p-4 sm:p-6 md:p-8 font-mono">
      <div className="max-w-7xl mx-auto space-y-6">
        <SciFiHeading level={1} className="text-center">
          PILOT MANAGEMENT
        </SciFiHeading>

        {/* Top row: Identity + Status */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* PILOT IDENTITY */}
          <SciFiPanel variant="primary" className="p-6">
            <h2 className="text-sm font-bold tracking-widest text-[#00ff41]/80 uppercase mb-4 border-b border-[#00ff41]/30 pb-2">
              PILOT IDENTITY
            </h2>
            <p className="text-lg font-bold text-[#00ff41] mb-4">
              🏷️ {pilot.name}
            </p>
            <div className="space-y-3">
              <SciFiInput
                label="Pilot Name"
                placeholder={pilot.name}
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                maxLength={20}
                disabled={nameUpdating}
                helpText="2〜20文字で入力してください"
              />
              {nameError && (
                <p className="text-red-400 text-sm">{nameError}</p>
              )}
              {nameSuccess && (
                <p className="text-[#00ff41] text-sm">{nameSuccess}</p>
              )}
              <SciFiButton
                onClick={handleUpdateName}
                disabled={nameUpdating || !nameInput.trim()}
                size="md"
                className="w-full"
              >
                {nameUpdating ? "UPDATING..." : "UPDATE PROFILE"}
              </SciFiButton>
            </div>
          </SciFiPanel>

          {/* STATUS & PARAMETERS */}
          <SciFiPanel variant="secondary" className="p-6">
            <h2 className="text-sm font-bold tracking-widest text-[#ffb000]/80 uppercase mb-4 border-b border-[#ffb000]/30 pb-2">
              STATUS &amp; PARAMETERS
            </h2>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-xs text-[#ffb000]/60 uppercase">Level</p>
                <p className="text-2xl font-bold text-[#ffb000]">{pilot.level}</p>
              </div>
              <div>
                <p className="text-xs text-[#ffb000]/60 uppercase">Skill Points</p>
                <p className="text-2xl font-bold text-[#00f0ff]">{pilot.skill_points} SP</p>
              </div>
            </div>

            <div className="mb-2">
              <div className="flex justify-between text-xs text-[#ffb000]/60 mb-1">
                <span>EXP</span>
                <span>{pilot.exp} / {requiredExp}</span>
              </div>
              <div className="w-full bg-[#1a1a1a] h-3 border border-[#ffb000]/30">
                <div
                  className="h-full bg-[#ffb000] transition-all duration-500"
                  style={{ width: `${expProgress}%` }}
                />
              </div>
            </div>

            <p className="text-sm text-[#ffb000]/80 mb-4">
              Credits: <span className="font-bold text-[#ffb000]">{pilot.credits.toLocaleString()} CR</span>
            </p>

            {/* Parameter Tuning Placeholder */}
            <div className="border border-[#ffb000]/20 bg-[#ffb000]/5 p-3">
              <p className="text-xs font-bold text-[#ffb000]/60 uppercase mb-2">
                🔒 Parameter Tuning{" "}
                <span className="text-[#ffb000]/40 normal-case font-normal">(Coming Soon)</span>
              </p>
              <div className="space-y-1 text-xs text-[#ffb000]/40">
                <p>&gt; Reflexes          : --</p>
                <p>&gt; Spatial Awareness : --</p>
                <p>&gt; Technical Skill   : --</p>
              </div>
            </div>
          </SciFiPanel>
        </div>

        {/* Skill messages */}
        {error && (
          <div className="border border-red-500 bg-red-900/20 p-3">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}
        {successMessage && (
          <div className="border border-[#00ff41] bg-[#00ff41]/10 p-3">
            <p className="text-[#00ff41] text-sm">{successMessage}</p>
          </div>
        )}

        {/* SKILL DEVELOPMENT */}
        <SciFiPanel variant="accent" className="p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4 border-b border-[#00f0ff]/30 pb-3">
            <h2 className="text-sm font-bold tracking-widest text-[#00f0ff]/80 uppercase">
              SKILL DEVELOPMENT
            </h2>
            {/* View mode toggle */}
            <div className="flex items-center gap-2 text-sm">
              <span className="text-[#00f0ff]/60 text-xs">View Mode:</span>
              <button
                onClick={() => setViewMode("list")}
                className={`px-3 py-1 border text-xs font-bold transition-colors ${
                  viewMode === "list"
                    ? "border-[#00f0ff] text-[#00f0ff] bg-[#00f0ff]/10"
                    : "border-[#00f0ff]/30 text-[#00f0ff]/40 hover:border-[#00f0ff]/60"
                }`}
              >
                ◉ List
              </button>
              <button
                onClick={() => setViewMode("tree")}
                className={`px-3 py-1 border text-xs font-bold transition-colors ${
                  viewMode === "tree"
                    ? "border-[#00f0ff] text-[#00f0ff] bg-[#00f0ff]/10"
                    : "border-[#00f0ff]/30 text-[#00f0ff]/40 hover:border-[#00f0ff]/60"
                }`}
              >
                ○ Tree (Beta)
              </button>
            </div>
          </div>

          {viewMode === "tree" ? (
            <div className="text-center py-12 text-[#00f0ff]/40">
              <p className="text-4xl mb-3">🔒</p>
              <p className="text-sm font-bold uppercase tracking-widest">Skill Tree — Coming Soon</p>
              <p className="text-xs mt-1">現在はリストモードでご利用ください</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {skills?.map((skill: SkillDefinition) => {
                const currentLevel = pilot.skills[skill.id] || 0;
                const isMaxLevel = currentLevel >= skill.max_level;
                const canUpgrade = pilot.skill_points > 0 && !isMaxLevel;
                const isUnlocking = unlocking === skill.id;

                return (
                  <SciFiCard key={skill.id} variant="accent" className="flex flex-col gap-3">
                    <div className="flex justify-between items-start">
                      <div className="flex-1 min-w-0 pr-2">
                        <h3 className="text-sm font-bold text-[#00f0ff]">{skill.name}</h3>
                        <p className="text-xs text-[#00f0ff]/60 mt-0.5">{skill.description}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-xs text-[#00f0ff]/60">Lv</p>
                        <p className="text-lg font-bold text-[#ffb000]">
                          {currentLevel}<span className="text-xs text-[#00f0ff]/40">/{skill.max_level}</span>
                        </p>
                      </div>
                    </div>

                    <div className="text-xs text-[#00f0ff]/70">
                      <span>効果: </span>
                      <span className="text-[#00f0ff] font-bold">+{skill.effect_per_level}% / Lv</span>
                      {currentLevel > 0 && (
                        <span className="ml-2 text-[#ffb000]">
                          (現在: +{(currentLevel * skill.effect_per_level).toFixed(1)}%)
                        </span>
                      )}
                    </div>

                    {isMaxLevel ? (
                      <div className="text-center py-2 border border-[#00f0ff]/20 text-xs text-[#00f0ff]/40 font-bold">
                        最大レベル
                      </div>
                    ) : pilot.skill_points === 0 ? (
                      <div className="text-center py-2 border border-[#ffb000]/20 text-xs text-[#ffb000]/40 font-bold">
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
          )}
        </SciFiPanel>
      </div>
    </div>
  );
}
