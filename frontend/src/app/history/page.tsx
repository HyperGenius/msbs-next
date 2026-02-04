/* frontend/src/app/history/page.tsx */
"use client";

import { useState } from "react";
import { useBattleHistory, useMissions } from "@/services/api";
import { BattleResult } from "@/types/battle";
import Header from "@/components/Header";
import Link from "next/link";

export default function HistoryPage() {
  const { battles, isLoading, isError } = useBattleHistory(50);
  const { missions } = useMissions();
  const [selectedBattle, setSelectedBattle] = useState<BattleResult | null>(null);

  const getMissionName = (missionId: number | null): string => {
    if (!missionId || !missions) return "Unknown Mission";
    const mission = missions.find((m) => m.id === missionId);
    return mission?.name || `Mission ${missionId}`;
  };

  return (
    <main className="min-h-screen bg-gray-900 text-green-400 p-8 font-mono">
      <div className="max-w-6xl mx-auto">
        <Header />

        <div className="mb-6 flex justify-between items-center">
          <h1 className="text-3xl font-bold border-l-4 border-green-500 pl-2">Battle History</h1>
          <Link
            href="/"
            className="px-4 py-2 bg-green-900 hover:bg-green-800 rounded font-bold transition-colors"
          >
            ← Back to Missions
          </Link>
        </div>

        {isLoading && (
          <div className="text-center py-12">
            <p className="text-xl">Loading battle history...</p>
          </div>
        )}

        {isError && (
          <div className="bg-red-900/30 border border-red-500 p-4 rounded">
            <p className="text-red-400">Failed to load battle history. Check if backend is running.</p>
          </div>
        )}

        {battles && battles.length === 0 && !isLoading && (
          <div className="bg-gray-800 border border-gray-700 p-8 rounded text-center">
            <p className="text-xl text-gray-400">No battle records found.</p>
            <p className="text-sm text-gray-500 mt-2">Complete some missions to see your history here.</p>
          </div>
        )}

        {battles && battles.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Battle List */}
            <div className="bg-gray-800 border border-green-800 rounded-lg p-4 max-h-[800px] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4 sticky top-0 bg-gray-800 pb-2">Records</h2>
              <div className="space-y-2">
                {battles.map((battle) => (
                  <button
                    key={battle.id}
                    onClick={() => setSelectedBattle(battle)}
                    className={`w-full text-left p-4 rounded border-2 transition-all ${
                      selectedBattle?.id === battle.id
                        ? "border-green-500 bg-green-900/30"
                        : "border-gray-700 hover:border-green-700"
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-bold">{getMissionName(battle.mission_id)}</span>
                      <span
                        className={`px-2 py-1 rounded text-xs font-bold ${
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
                    <p className="text-xs text-gray-400">
                      {new Date(battle.created_at).toLocaleString("ja-JP")}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Turns: {battle.logs.length > 0 ? battle.logs[battle.logs.length - 1].turn : 0}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            {/* Battle Detail */}
            <div className="bg-gray-800 border border-green-800 rounded-lg p-4 max-h-[800px] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4 sticky top-0 bg-gray-800 pb-2">Battle Log</h2>
              {!selectedBattle ? (
                <div className="text-center py-12 text-gray-400">
                  <p>Select a battle to view details</p>
                </div>
              ) : (
                <div>
                  <div className="mb-4 pb-4 border-b border-gray-700">
                    <h3 className="font-bold text-lg mb-2">{getMissionName(selectedBattle.mission_id)}</h3>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">
                        {new Date(selectedBattle.created_at).toLocaleString("ja-JP")}
                      </span>
                      <span
                        className={`px-3 py-1 rounded font-bold ${
                          selectedBattle.win_loss === "WIN"
                            ? "bg-green-900 text-green-300"
                            : selectedBattle.win_loss === "LOSE"
                            ? "bg-red-900 text-red-300"
                            : "bg-yellow-900 text-yellow-300"
                        }`}
                      >
                        {selectedBattle.win_loss}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-1 text-sm font-mono">
                    {selectedBattle.logs.map((log, index) => (
                      <div
                        key={index}
                        className="border-l-2 border-green-900 pl-2 py-1 text-green-600"
                      >
                        <span className="opacity-50 mr-2">[Turn {log.turn}]</span>
                        <span>{log.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
