/* frontend/src/components/history/BattleDetailModal.tsx */
"use client";

import { useState } from "react";
import { BattleResult, BattleLog, MobileSuit } from "@/types/battle";
import BattleViewer from "@/components/BattleViewer";
import ModalHeader from "./ModalHeader";
import TurnController from "./TurnController";
import BattleLogViewer from "./BattleLogViewer";
import { useBattleLogic } from "@/hooks/useBattleLogic";
import { useBattleLogs } from "@/services/api";
import { IS_PRODUCTION } from "@/constants";

interface BattleDetailModalProps {
  battle: BattleResult;
  missionName: string;
  mobileSuits: MobileSuit[] | undefined;
  onClose: () => void;
}

export default function BattleDetailModal({
  battle,
  missionName,
  mobileSuits,
  onClose,
}: BattleDetailModalProps) {
  const [currentTimestamp, setCurrentTimestamp] = useState(0);
  const [isFiltered, setIsFiltered] = useState(IS_PRODUCTION);
  // 開発環境専用: 本番ログの抽象化をプレビューするトグル
  const [isProductionPreview, setIsProductionPreview] = useState(false);

  // バトルログを遅延ロード（リプレイ用）
  const { logs: fetchedLogs, isLoading: logsLoading } = useBattleLogs(battle.id);
  const logs: BattleLog[] = fetchedLogs ?? [];

  const { ownedMobileSuitIds, playerId, filterRelevantLogs } = useBattleLogic(
    battle,
    mobileSuits,
    isFiltered
  );

  const maxTimestamp = logs.length
    ? logs[logs.length - 1].timestamp
    : 0;

  const hasReplayData = !!(
    battle.player_info &&
    battle.enemies_info &&
    battle.enemies_info.length > 0
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 border border-green-800 rounded-lg w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <ModalHeader battle={battle} missionName={missionName} onClose={onClose} />

        {/* Modal Body — BattleViewer は固定、ログのみスクロール */}
        <div className="flex flex-col flex-1 min-h-0">
          {/* 上部固定: 3D Replay Viewer + ターンコントローラー */}
          <div className="flex-none p-4 border-b border-gray-700">
            {hasReplayData ? (
              <>
                <BattleViewer
                  logs={logs}
                  player={battle.player_info as MobileSuit}
                  enemies={battle.enemies_info as MobileSuit[]}
                  currentTimestamp={currentTimestamp}
                  environment={battle.environment || "SPACE"}
                />
                <TurnController
                  currentTimestamp={currentTimestamp}
                  maxTimestamp={maxTimestamp}
                  onTimestampChange={setCurrentTimestamp}
                />
              </>
            ) : (
              <div className="p-3 bg-yellow-900/20 border border-yellow-700 rounded" role="alert">
                <p className="text-yellow-400 text-sm">
                  ⚠ このバトルログにはリプレイに必要な機体データが含まれていません
                </p>
              </div>
            )}
          </div>

          {/* 下部スクロール: ログ一覧 */}
          {logsLoading ? (
            <div className="flex-1 flex items-center justify-center p-4">
              <p className="text-gray-400 text-sm">ログを読み込み中...</p>
            </div>
          ) : (
            <BattleLogViewer
              logs={logs}
              currentTimestamp={currentTimestamp}
              isFiltered={isFiltered}
              isProductionPreview={isProductionPreview}
              hasReplayData={hasReplayData}
              playerId={playerId}
              ownedMobileSuitIds={ownedMobileSuitIds}
              filterRelevantLogs={filterRelevantLogs}
              onFilterToggle={() => setIsFiltered((v) => !v)}
              onProductionPreviewToggle={() => setIsProductionPreview((v) => !v)}
            />
          )}
        </div>
      </div>
    </div>
  );
}
