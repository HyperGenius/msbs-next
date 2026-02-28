/* frontend/src/app/history/page.tsx */
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBattleHistory, useMissions, useMobileSuits } from "@/services/api";
import { BattleLog, BattleResult, MobileSuit } from "@/types/battle";
import BattleViewer from "@/components/BattleViewer";
import Link from "next/link";

export default function HistoryPage() {
  const { battles, isLoading, isError } = useBattleHistory(50);
  const { missions } = useMissions();
  const { mobileSuits } = useMobileSuits();
  const [selectedBattle, setSelectedBattle] = useState<BattleResult | null>(null);
  const [currentTurn, setCurrentTurn] = useState(0);
  const [isFiltered, setIsFiltered] = useState(false);
  const logContainerRef = useRef<HTMLDivElement>(null);

  const ownedMobileSuitIds = useMemo(
    () => new Set(mobileSuits?.map((ms) => ms.id) ?? []),
    [mobileSuits]
  );

  /** player_info から自機・僚機の ID セットを算出 */
  const playerTeamIds = useMemo(() => {
    if (!selectedBattle?.player_info) return new Set<string>();
    const playerInfo = selectedBattle.player_info;
    const teamId = playerInfo.team_id ?? playerInfo.id;
    const ids = new Set<string>([playerInfo.id]);
    // 同じ team_id を持つ僚機を追加
    if (selectedBattle.enemies_info) {
      for (const e of selectedBattle.enemies_info) {
        if ((e.team_id ?? e.id) === teamId) {
          ids.add(e.id);
        }
      }
    }
    return ids;
  }, [selectedBattle]);

  const playerId = selectedBattle?.player_info?.id ?? null;

  /** ログフィルタリング: 自機/僚機のアクション or 自機がターゲット */
  const filterRelevantLogs = useCallback(
    (logs: BattleLog[]): BattleLog[] => {
      if (!isFiltered || !playerId) return logs;
      return logs.filter(
        (log) =>
          playerTeamIds.has(log.actor_id) ||
          (log.target_id != null && log.target_id === playerId)
      );
    },
    [isFiltered, playerId, playerTeamIds]
  );

  /** currentTurn 変更時に該当ターンのログへ自動スクロール */
  useEffect(() => {
    if (!logContainerRef.current || !selectedBattle) return;
    const target = logContainerRef.current.querySelector(
      `[data-turn-start="${currentTurn}"]`
    );
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [currentTurn, selectedBattle]);

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

  const handleSelectBattle = (battle: BattleResult) => {
    setSelectedBattle(battle);
    setCurrentTurn(0);
  };

  const maxTurn = selectedBattle?.logs.length
    ? selectedBattle.logs[selectedBattle.logs.length - 1].turn
    : 0;

  const hasReplayData = !!(
    selectedBattle?.player_info &&
    selectedBattle?.enemies_info &&
    selectedBattle.enemies_info.length > 0
  );

  return (
    <main className="min-h-screen bg-gray-900 text-green-400 p-8 font-mono">
      <div className="max-w-6xl mx-auto">

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
          <div className="max-w-2xl mx-auto">
            {/* Battle List */}
            <div className="bg-gray-800 border border-green-800 rounded-lg p-4 max-h-[800px] overflow-y-auto">
              <h2 className="text-xl font-bold mb-4 sticky top-0 bg-gray-800 pb-2">Records</h2>
              <div className="space-y-2">
                {battles.map((battle) => (
                  <button
                    key={battle.id}
                    onClick={() => handleSelectBattle(battle)}
                    className="w-full text-left p-4 rounded border-2 border-gray-700 hover:border-green-700 transition-all"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-bold">{getMissionName(battle.mission_id, battle.created_at)}</span>
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
          </div>
        )}

        {/* Battle Detail Modal */}
        {selectedBattle && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in"
            onClick={() => setSelectedBattle(null)}
          >
            <div
              className="bg-gray-800 border border-green-800 rounded-lg w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="flex items-start justify-between p-4 border-b border-gray-700">
                <div>
                  <h3 className="font-bold text-lg">{getMissionName(selectedBattle.mission_id, selectedBattle.created_at)}</h3>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-gray-400 text-sm">
                      {new Date(selectedBattle.created_at).toLocaleString("ja-JP")}
                    </span>
                    <span
                      className={`px-3 py-1 rounded font-bold text-sm ${
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
                <button
                  onClick={() => setSelectedBattle(null)}
                  className="text-gray-400 hover:text-white text-2xl leading-none ml-4 transition-colors"
                  aria-label="閉じる"
                >
                  ✕
                </button>
              </div>

              {/* Modal Body */}
              <div className="overflow-y-auto flex-1 p-4">
                {/* 3D Replay Viewer */}
                {hasReplayData ? (
                  <div className="mb-4">
                    <BattleViewer
                      logs={selectedBattle.logs}
                      player={selectedBattle.player_info as MobileSuit}
                      enemies={selectedBattle.enemies_info as MobileSuit[]}
                      currentTurn={currentTurn}
                      environment={selectedBattle.environment || "SPACE"}
                    />

                    {/* Turn Controller */}
                    <div className="mt-2 p-3 bg-gray-900 border border-green-800 rounded">
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => setCurrentTurn(Math.max(0, currentTurn - 1))}
                          disabled={currentTurn <= 0}
                          className="px-3 py-1 bg-green-900 hover:bg-green-800 disabled:opacity-30 rounded text-sm font-bold transition-colors"
                        >
                          &lt; PREV
                        </button>
                        <div className="flex-grow flex flex-col">
                          <input
                            type="range"
                            min="0"
                            max={maxTurn}
                            value={currentTurn}
                            onChange={(e) => setCurrentTurn(Number(e.target.value))}
                            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-green-500"
                          />
                          <div className="flex justify-between text-xs mt-1 text-green-600/60">
                            <span>Start</span>
                            <span>Turn: {currentTurn} / {maxTurn}</span>
                            <span>End</span>
                          </div>
                        </div>
                        <button
                          onClick={() => setCurrentTurn(Math.min(maxTurn, currentTurn + 1))}
                          disabled={currentTurn >= maxTurn}
                          className="px-3 py-1 bg-green-900 hover:bg-green-800 disabled:opacity-30 rounded text-sm font-bold transition-colors"
                        >
                          NEXT &gt;
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="mb-4 p-3 bg-yellow-900/20 border border-yellow-700 rounded" role="alert">
                    <p className="text-yellow-400 text-sm">
                      ⚠ このバトルログにはリプレイに必要な機体データが含まれていません
                    </p>
                  </div>
                )}

                {/* Log Filter Toggle */}
                {hasReplayData && (
                  <div className="flex items-center gap-2 mb-2">
                    <button
                      onClick={() => setIsFiltered((v) => !v)}
                      className={`px-3 py-1 rounded text-xs font-bold transition-colors ${
                        isFiltered
                          ? "bg-blue-700 text-blue-100"
                          : "bg-gray-700 text-gray-300 hover:bg-gray-600"
                      }`}
                    >
                      {isFiltered ? "🔍 自機関連のみ表示中" : "🔍 ログフィルター: OFF"}
                    </button>
                  </div>
                )}

                <div ref={logContainerRef} className="space-y-1 text-sm font-mono">
                  {(() => {
                    const displayedLogs = filterRelevantLogs(selectedBattle.logs);
                    const seenTurns = new Set<number>();
                    return displayedLogs.map((log, index) => {
                      const isOwnUnit = ownedMobileSuitIds.has(log.actor_id);
                      const isActiveTurn = log.turn === currentTurn;
                      const isFirstOfTurn = !seenTurns.has(log.turn);
                      if (isFirstOfTurn) seenTurns.add(log.turn);
                      return (
                        <div
                          key={index}
                          {...(isFirstOfTurn ? { "data-turn-start": log.turn } : {})}
                          className={`border-l-2 pl-2 py-1 transition-colors ${
                            isActiveTurn
                              ? "border-green-400 bg-green-900/40 text-green-200 shadow-[0_0_8px_rgba(34,197,94,0.3)]"
                              : isOwnUnit
                              ? "border-blue-500 bg-blue-900/30 text-blue-300"
                              : "border-green-900 text-green-600"
                          }`}
                        >
                          <span className="opacity-50 mr-2">[Turn {log.turn}]</span>
                          <span>{log.message}</span>
                        </div>
                      );
                    });
                  })()}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
