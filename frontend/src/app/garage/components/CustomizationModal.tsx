"use client";

import { useState } from "react";
import { MobileSuit, Pilot } from "@/types/battle";
import { SciFiButton, SciFiHeading, SciFiPanel } from "@/components/ui";
import StatusTab from "./StatusTab";
import SpecsDisplay from "./SpecsDisplay";
import LoadoutManager from "./LoadoutManager";
import TacticsSelector from "./TacticsSelector";

type TabKey = "STATUS" | "TERRAIN" | "LOADOUT" | "TACTICS";

interface FormData {
  name: string;
  max_hp: number;
  armor: number;
  mobility: number;
  tactics: {
    priority: "CLOSEST" | "WEAKEST" | "RANDOM" | "STRONGEST" | "THREAT";
    range: "MELEE" | "RANGED" | "BALANCED" | "FLEE";
  };
}

const TABS: { key: TabKey; label: string }[] = [
  { key: "STATUS", label: "STATUS" },
  { key: "TERRAIN", label: "TERRAIN" },
  { key: "LOADOUT", label: "LOADOUT" },
  { key: "TACTICS", label: "TACTICS" },
];

interface CustomizationModalProps {
  mobileSuit: MobileSuit;
  pilot: Pilot | undefined;
  formData: FormData;
  isSaving: boolean;
  successMessage: string | null;
  onFormDataChange: (formData: FormData) => void;
  onSubmit: (e: React.FormEvent) => void;
  onOpenWeaponModal: (slotIndex: number) => void;
  onUpgraded: (updatedMs: MobileSuit) => void;
  onClose: () => void;
}

export default function CustomizationModal({
  mobileSuit,
  pilot,
  formData,
  isSaving,
  successMessage,
  onFormDataChange,
  onSubmit,
  onOpenWeaponModal,
  onUpgraded,
  onClose,
}: CustomizationModalProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("STATUS");

  return (
    <div
      className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-40"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-4xl mx-4 h-[90vh] flex flex-col">
        <SciFiPanel variant="accent" chiseled={true}>
          <div className="flex flex-col max-h-[90vh]">
            {/* Header */}
            <div className="p-4 sm:p-6 border-b border-[#00f0ff]/30 flex-shrink-0">
              <div className="flex justify-between items-start">
                <div>
                  <SciFiHeading level={3} variant="accent" className="text-lg sm:text-xl">
                    {mobileSuit.name}
                  </SciFiHeading>
                  <p className="text-xs text-[#00f0ff]/60 mt-1">
                    CUSTOMIZATION INTERFACE
                  </p>
                </div>
                <SciFiButton variant="danger" size="sm" onClick={onClose}>
                  ✕ CLOSE
                </SciFiButton>
              </div>

              {/* Tab Navigation */}
              <div className="flex gap-1 mt-4 overflow-x-auto">
                {TABS.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`px-4 py-2 text-xs sm:text-sm font-bold font-mono tracking-wider transition-all whitespace-nowrap ${
                      activeTab === tab.key
                        ? "bg-[#00f0ff]/20 text-[#00f0ff] border-b-2 border-[#00f0ff]"
                        : "text-[#00f0ff]/40 hover:text-[#00f0ff]/70 hover:bg-[#00f0ff]/5"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Tab Content */}
            <div className="p-4 sm:p-6 overflow-y-auto flex-1">
              {activeTab === "STATUS" && (
                <StatusTab
                  mobileSuit={mobileSuit}
                  pilot={pilot}
                  onUpgraded={onUpgraded}
                />
              )}

              {activeTab === "TERRAIN" && (
                <SpecsDisplay selectedMs={mobileSuit} />
              )}

              {activeTab === "LOADOUT" && (
                <LoadoutManager
                  selectedMs={mobileSuit}
                  onOpenWeaponModal={onOpenWeaponModal}
                />
              )}

              {activeTab === "TACTICS" && (
                <form onSubmit={onSubmit} className="space-y-4">
                  <TacticsSelector
                    tactics={formData.tactics}
                    onChange={(tactics) => onFormDataChange({ ...formData, tactics })}
                  />

                  {/* Success Message */}
                  {successMessage && (
                    <SciFiPanel variant="primary" chiseled={false}>
                      <div className="p-3 text-[#00ff41] animate-pulse text-sm">
                        {successMessage}
                      </div>
                    </SciFiPanel>
                  )}

                  {/* Submit */}
                  <SciFiButton
                    type="submit"
                    disabled={isSaving}
                    variant="accent"
                    size="lg"
                    className="w-full"
                  >
                    {isSaving ? "保存中..." : "戦術を保存"}
                  </SciFiButton>
                </form>
              )}
            </div>
          </div>
        </SciFiPanel>
      </div>
    </div>
  );
}
