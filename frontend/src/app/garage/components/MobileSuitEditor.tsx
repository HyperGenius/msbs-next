/* frontend/src/app/garage/components/MobileSuitEditor.tsx */
"use client";

import { MobileSuit } from "@/types/battle";
import {
  SciFiButton,
  SciFiHeading,
  SciFiInput,
  SciFiPanel,
} from "@/components/ui";
import SpecsDisplay from "./SpecsDisplay";
import LoadoutManager from "./LoadoutManager";
import TacticsSelector from "./TacticsSelector";

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

interface MobileSuitEditorProps {
  selectedMs: MobileSuit | null;
  formData: FormData;
  isSaving: boolean;
  successMessage: string | null;
  onFormDataChange: (formData: FormData) => void;
  onSubmit: (e: React.FormEvent) => void;
  onOpenWeaponModal: (slotIndex: number) => void;
}

export default function MobileSuitEditor({
  selectedMs,
  formData,
  isSaving,
  successMessage,
  onFormDataChange,
  onSubmit,
  onOpenWeaponModal,
}: MobileSuitEditorProps) {
  return (
    <SciFiPanel variant="accent">
      <div className="p-4 sm:p-6">
        <SciFiHeading
          level={3}
          className="mb-4 text-lg sm:text-xl"
          variant="accent"
        >
          機体ステータス編集
        </SciFiHeading>

        {selectedMs ? (
          <form onSubmit={onSubmit} className="space-y-4">
            {/* 名前 */}
            <SciFiInput
              label="機体名"
              type="text"
              value={formData.name}
              onChange={(e) =>
                onFormDataChange({ ...formData, name: e.target.value })
              }
              variant="accent"
            />

            {/* Max HP */}
            <SciFiInput
              label="最大HP"
              type="number"
              value={formData.max_hp}
              onChange={(e) =>
                onFormDataChange({
                  ...formData,
                  max_hp: Number(e.target.value),
                })
              }
              variant="accent"
            />

            {/* Armor */}
            <SciFiInput
              label="装甲"
              type="number"
              value={formData.armor}
              onChange={(e) =>
                onFormDataChange({
                  ...formData,
                  armor: Number(e.target.value),
                })
              }
              variant="accent"
            />

            {/* Mobility */}
            <SciFiInput
              label="機動性"
              type="number"
              step="0.1"
              value={formData.mobility}
              onChange={(e) =>
                onFormDataChange({
                  ...formData,
                  mobility: Number(e.target.value),
                })
              }
              variant="accent"
            />

            {/* Specs Display */}
            <SpecsDisplay selectedMs={selectedMs} />

            {/* Loadout */}
            <LoadoutManager
              selectedMs={selectedMs}
              onOpenWeaponModal={onOpenWeaponModal}
            />

            {/* Tactics */}
            <TacticsSelector
              tactics={formData.tactics}
              onChange={(tactics) => onFormDataChange({ ...formData, tactics })}
            />

            {/* Success Message */}
            {successMessage && (
              <SciFiPanel variant="primary" chiseled={false}>
                <div className="p-3 text-[#00ff41] animate-pulse">
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
              {isSaving ? "保存中..." : "保存"}
            </SciFiButton>
          </form>
        ) : (
          <div className="flex items-center justify-center h-64 text-[#00ff41]/30">
            <p>機体を選択してください</p>
          </div>
        )}
      </div>
    </SciFiPanel>
  );
}
