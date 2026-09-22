/* frontend/src/components/history/BattleDetailModal.tsx */
"use client";

import { useState } from "react";
import { BattleResult, MobileSuit } from "@/types/battle";
import BattleViewer from "@/components/BattleViewer";
import ChapterTrack from "@/components/BattleViewer/ui/ChapterTrack";
import { useBattleChapters } from "@/components/BattleViewer/hooks/useBattleChapters";
import ModalHeader from "./ModalHeader";
import TurnController from "./TurnController";
import BattleSummaryPanel from "./BattleSummaryPanel";
import { useBattleLogs } from "@/services/api";

interface BattleDetailModalProps {
  battle: BattleResult;
  missionName: string;
  onClose: () => void;
}

export default function BattleDetailModal({
  battle,
  missionName,
  onClose,
}: BattleDetailModalProps) {
  const [currentTimestamp, setCurrentTimestamp] = useState(0);

  // バトルログを遅延ロード（リプレイ用）。全件ダウンロード完了を待たず、
  // 届いた分から段階的に反映する（Issue #494）。isLoadingは初回データ到達まで、
  // isStreamingは全件パース完了までtrueになる
  const { logs: fetchedLogs, isLoading: logsLoading, isStreaming: logsStreaming } = useBattleLogs(battle.id);
  const logs = fetchedLogs ?? [];

  const playerId = battle.player_info?.id ?? null;
  const enemies = (battle.enemies_info ?? []) as MobileSuit[];

  const chapters = useBattleChapters(
    logs,
    playerId && battle.player_info ? { id: playerId, name: battle.player_info.name } : null,
    enemies
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
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 border border-green-800 rounded-lg w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <ModalHeader battle={battle} missionName={missionName} onClose={onClose} />

        {/* Modal Body — BattleViewer は固定、戦果サマリーのみスクロール */}
        <div className="flex flex-col flex-1 min-h-0">
          {/* 上部固定: 3D Replay Viewer + ターンコントローラー */}
          <div className="flex-none p-4 border-b border-gray-700">
            {hasReplayData ? (
              logsLoading ? (
                // ログ読み込み完了前にBattleViewerをマウントすると、
                // 実ログ未確定の仮位置でカメラが初期配置されてしまい、
                // ログ読み込み完了後の再描画で自機が視界外に外れる不具合があった（Issue #425）。
                // ログ確定後にマウントすることで、確定した初期位置を基準にカメラを配置させる。
                <div className="w-full h-[300px] sm:h-[400px] md:h-[500px] rounded border border-green-800 mb-4 flex items-center justify-center bg-gray-900/50">
                  <p className="text-gray-400 text-sm">ビューアを準備中...</p>
                </div>
              ) : (
                <>
                  <BattleViewer
                    logs={logs}
                    player={battle.player_info as MobileSuit}
                    enemies={battle.enemies_info as MobileSuit[]}
                    obstacles={battle.obstacles_info}
                    mapBounds={battle.map_bounds}
                    currentTimestamp={currentTimestamp}
                    environment={battle.environment || "SPACE"}
                  />
                  {/* ログを裏で読み込み中でも再生をブロックしない。読み込み継続中であることだけ
                      控えめに示す（全件到着まで待たされないUX、Issue #494） */}
                  {logsStreaming && (
                    <div className="mb-2 flex items-center gap-2 text-xs text-green-600/70" role="status">
                      <span className="inline-block w-3 h-3 border-2 border-green-600/40 border-t-green-400 rounded-full animate-spin" />
                      <span>続きのログを読み込み中... （{logs.length.toLocaleString()}件到着済み）</span>
                    </div>
                  )}
                  {/* チャプタートラック: 3Dビューア直下に常駐し、有意なイベントのみクリックでジャンプする（Issue #521） */}
                  <ChapterTrack chapters={chapters} currentTimestamp={currentTimestamp} onSeek={setCurrentTimestamp} />
                  <TurnController
                    currentTimestamp={currentTimestamp}
                    maxTimestamp={maxTimestamp}
                    isStreaming={logsStreaming}
                    onTimestampChange={setCurrentTimestamp}
                  />
                </>
              )
            ) : (
              <div className="p-3 bg-yellow-900/20 border border-yellow-700 rounded" role="alert">
                <p className="text-yellow-400 text-sm">
                  ⚠ このバトルログにはリプレイに必要な機体データが含まれていません
                </p>
              </div>
            )}
          </div>

          {/* 下部スクロール: 戦果サマリー（タブ切り替えなしの常時表示、Issue #521）。初回データ到着後は、
              残りが裏で読み込み中でも到着済みの分から表示する（全件到着まで待たせない、Issue #494） */}
          <div className="flex-1 min-h-0 overflow-y-auto p-4">
            {logsLoading ? (
              <div className="flex items-center justify-center p-4">
                <p className="text-gray-400 text-sm">ログを読み込み中...</p>
              </div>
            ) : (
              <BattleSummaryPanel battle={battle} logs={logs} playerId={playerId} enemies={enemies} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
