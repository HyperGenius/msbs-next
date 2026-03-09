/* frontend/src/components/history/BattleLogViewer.tsx */
"use client";

import { useEffect, useRef } from "react";
import { BattleLog } from "@/types/battle";
import { formatBattleLog } from "@/utils/logFormatter";
import { IS_PRODUCTION } from "@/constants";

interface BattleLogViewerProps {
  logs: BattleLog[];
  currentTurn: number;
  isFiltered: boolean;
  isProductionPreview: boolean;
  hasReplayData: boolean;
  playerId: string | null;
  ownedMobileSuitIds: Set<string>;
  filterRelevantLogs: (logs: BattleLog[]) => BattleLog[];
  onFilterToggle: () => void;
  onProductionPreviewToggle: () => void;
}

export default function BattleLogViewer({
  logs,
  currentTurn,
  isFiltered,
  isProductionPreview,
  hasReplayData,
  playerId,
  ownedMobileSuitIds,
  filterRelevantLogs,
  onFilterToggle,
  onProductionPreviewToggle,
}: BattleLogViewerProps) {
  const logContainerRef = useRef<HTMLDivElement>(null);

  /** currentTurn 変更時に該当ターンのログへ自動スクロール */
  useEffect(() => {
    if (!logContainerRef.current) return;
    const target = logContainerRef.current.querySelector(
      `[data-turn-start="${currentTurn}"]`
    );
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [currentTurn]);

  const displayedLogs = filterRelevantLogs(logs);
  const seenTurns = new Set<number>();

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {/* Log Filter Toggle — 本番環境では非表示 */}
      {hasReplayData && !IS_PRODUCTION && (
        <div className="flex items-center gap-2 mb-2">
          <button
            onClick={onFilterToggle}
            aria-label={isFiltered ? "ログフィルター解除" : "自機関連ログのみ表示"}
            className={`px-3 py-1 rounded text-xs font-bold transition-colors ${
              isFiltered
                ? "bg-blue-700 text-blue-100"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            {isFiltered ? "自機関連のみ表示中" : "ログフィルター: OFF"}
          </button>
          <button
            onClick={onProductionPreviewToggle}
            aria-label={isProductionPreview ? "開発表示に切り替え" : "本番表示プレビューに切り替え"}
            className={`px-3 py-1 rounded text-xs font-bold transition-colors ${
              isProductionPreview
                ? "bg-yellow-700 text-yellow-100"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            {isProductionPreview ? "本番プレビュー中" : "本番プレビュー: OFF"}
          </button>
        </div>
      )}

      <div ref={logContainerRef} className="space-y-1 text-sm font-mono">
        {displayedLogs.map((log, index) => {
          const displayLog = formatBattleLog(log, IS_PRODUCTION || isProductionPreview, playerId ?? "");
          const isOwnUnit = ownedMobileSuitIds.has(log.actor_id);
          const isActiveTurn = log.turn === currentTurn;
          const isFirstOfTurn = !seenTurns.has(log.turn);
          if (isFirstOfTurn) seenTurns.add(log.turn);
          return (
            <div
              key={index}
              data-turn-start={isFirstOfTurn ? log.turn : undefined}
              className={`border-l-2 pl-2 py-1 transition-colors ${
                isActiveTurn
                  ? "border-green-400 bg-green-900/40 text-green-200 shadow-[0_0_8px_rgba(34,197,94,0.3)]"
                  : isOwnUnit
                  ? "border-blue-500 bg-blue-900/30 text-blue-300"
                  : "border-green-900 text-green-600"
              }`}
            >
              <span className="opacity-50 mr-2">[Turn {log.turn}]</span>
              <span>{displayLog.message}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
