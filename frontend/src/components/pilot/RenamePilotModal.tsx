"use client";

import { useState } from "react";
import { Pilot } from "@/types/battle";
import { updatePilotName } from "@/services/api";
import { KeyedMutator } from "swr";
import SciFiPanel from "@/components/ui/SciFiPanel";
import SciFiInput from "@/components/ui/SciFiInput";
import SciFiButton from "@/components/ui/SciFiButton";

interface RenamePilotModalProps {
  pilot: Pilot;
  onClose: () => void;
  mutatePilot: KeyedMutator<Pilot>;
}

export default function RenamePilotModal({ pilot, onClose, mutatePilot }: RenamePilotModalProps) {
  const [nameInput, setNameInput] = useState<string>("");
  const [nameError, setNameError] = useState<string>("");
  const [nameSuccess, setNameSuccess] = useState<string>("");
  const [nameUpdating, setNameUpdating] = useState<boolean>(false);

  const handleUpdateName = async () => {
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

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <SciFiPanel variant="primary" className="p-6">
          <h2 className="text-sm font-bold tracking-widest text-[#00ff41] uppercase mb-1 border-b border-[#00ff41]/30 pb-2">
            RENAME PILOT
          </h2>
          <p className="text-xs text-gray-400 mb-4">現在の名前: {pilot.name}</p>

          <div className="space-y-3">
            <SciFiInput
              label="New Pilot Name"
              placeholder="2〜20文字で入力"
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

            <div className="flex gap-3 pt-1">
              <SciFiButton
                onClick={handleUpdateName}
                disabled={nameUpdating || !nameInput.trim()}
                size="md"
                className="flex-1"
              >
                {nameUpdating ? "UPDATING..." : "CONFIRM"}
              </SciFiButton>
              <SciFiButton
                onClick={onClose}
                disabled={nameUpdating}
                size="md"
                className="flex-1"
              >
                CANCEL
              </SciFiButton>
            </div>
          </div>
        </SciFiPanel>
      </div>
    </div>
  );
}
