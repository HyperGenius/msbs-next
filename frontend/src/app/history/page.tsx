/* frontend/src/app/history/page.tsx */
"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { useBattleHistory, useMissions, useMobileSuits } from "@/services/api";
import { BattleResult } from "@/types/battle";
import BattleList from "@/components/history/BattleList";
import BattleDetailModal from "@/components/history/BattleDetailModal";

export default function HistoryPage() {
  const { isLoaded } = useAuth();
  const { battles, isLoading, isError } = useBattleHistory(50);
  const { missions } = useMissions();
  const { mobileSuits } = useMobileSuits();
  const [selectedBattle, setSelectedBattle] = useState<BattleResult | null>(null);
  const [clerkTimedOut, setClerkTimedOut] = useState(false);

  // Clerk の初期化が長時間（2秒）完了しない場合はタイムアウトとして扱う
  // スマートフォンエミュレーション時などでCDNスクリプトの読み込みが遅い場合の対策
  useEffect(() => {
    if (isLoaded) {
      setClerkTimedOut(false);
      return;
    }
    const timer = setTimeout(() => setClerkTimedOut(true), 2000);
    return () => clearTimeout(timer);
  }, [isLoaded]);

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

        {clerkTimedOut && !isLoaded ? (
          <div className="bg-yellow-900/30 border border-yellow-500 p-6 rounded text-center">
            <p className="text-yellow-400 mb-4">認証の初期化に時間がかかっています。</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-yellow-700 hover:bg-yellow-600 text-yellow-100 border border-yellow-500 transition-colors font-mono"
            >
              ページを再読み込み
            </button>
          </div>
        ) : (
          <BattleList
            battles={battles ?? []}
            isLoading={isLoading}
            isError={isError}
            onSelectBattle={setSelectedBattle}
            getMissionName={getMissionName}
          />
        )}

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
