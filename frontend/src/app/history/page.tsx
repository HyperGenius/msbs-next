/* frontend/src/app/history/page.tsx */
"use client";

import { useState } from "react";
import { useBattleHistory, useMissions, useMobileSuits } from "@/services/api";
import { BattleResult } from "@/types/battle";
import BattleList from "@/components/history/BattleList";
import BattleDetailModal from "@/components/history/BattleDetailModal";

export default function HistoryPage() {
  const { battles, isLoading, isError } = useBattleHistory(50);
  const { missions } = useMissions();
  const { mobileSuits } = useMobileSuits();
  const [selectedBattle, setSelectedBattle] = useState<BattleResult | null>(null);

  const getMissionName = (missionId: number | null, createdAt?: string): string => {
    if (missionId && missions) {
      const mission = missions.find((m) => m.id === missionId);
      return mission?.name || `Mission ${missionId}`;
    }
    if (!missionId) {
      if (createdAt) {
        const d = new Date(createdAt);
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, "0");
        const dd = String(d.getDate()).padStart(2, "0");
        return `${yyyy}${mm}${dd} デイリーバトルロイヤル`;
      }
      return "デイリーバトルロイヤル";
    }
    return "Unknown Mission";
  };

  return (
    <main className="min-h-screen bg-gray-900 text-green-400 p-8 font-mono">
      <div className="max-w-6xl mx-auto">

        <div className="mb-6 flex justify-between items-center">
          <h1 className="text-3xl font-bold border-l-4 border-green-500 pl-2">Battle History</h1>
        </div>

        <BattleList
          battles={battles ?? []}
          isLoading={isLoading}
          isError={isError}
          onSelectBattle={setSelectedBattle}
          getMissionName={getMissionName}
        />

        {selectedBattle && (
          <BattleDetailModal
            battle={selectedBattle}
            missionName={getMissionName(selectedBattle.mission_id, selectedBattle.created_at)}
            mobileSuits={mobileSuits}
            onClose={() => setSelectedBattle(null)}
          />
        )}
      </div>
    </main>
  );
}
