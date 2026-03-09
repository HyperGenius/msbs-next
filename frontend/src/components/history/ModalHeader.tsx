/* frontend/src/components/history/ModalHeader.tsx */
"use client";

import { BattleResult } from "@/types/battle";

interface ModalHeaderProps {
  battle: BattleResult;
  missionName: string;
  onClose: () => void;
}

export default function ModalHeader({ battle, missionName, onClose }: ModalHeaderProps) {
  return (
    <div className="flex items-start justify-between p-4 border-b border-gray-700">
      <div>
        <h3 className="font-bold text-lg">{missionName}</h3>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-gray-400 text-sm">
            {new Date(battle.created_at).toLocaleString("ja-JP")}
          </span>
          <span
            className={`px-3 py-1 rounded font-bold text-sm ${
              battle.win_loss === "WIN"
                ? "bg-green-900 text-green-300"
                : battle.win_loss === "LOSE"
                ? "bg-red-900 text-red-300"
                : "bg-yellow-900 text-yellow-300"
            }`}
          >
            {battle.win_loss}
          </span>
        </div>
      </div>
      <button
        onClick={onClose}
        className="text-gray-400 hover:text-white text-2xl leading-none ml-4 transition-colors"
        aria-label="閉じる"
      >
        ✕
      </button>
    </div>
  );
}
