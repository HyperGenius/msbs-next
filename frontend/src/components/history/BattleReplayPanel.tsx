/* frontend/src/components/history/BattleReplayPanel.tsx */
"use client";

import { useMemo, useState } from "react";
import { BattleLog, BattleResult, MobileSuit } from "@/types/battle";
import BattleViewer from "@/components/BattleViewer";
import ChapterTrack from "@/components/BattleViewer/ui/ChapterTrack";
import { useBattleChapters } from "@/components/BattleViewer/hooks/useBattleChapters";
import TurnController from "./TurnController";
import BattleSummaryPanel from "./BattleSummaryPanel";
import { getViewerEnvironment } from "@/utils/theater";

interface BattleReplayPanelProps {
  battle: BattleResult;
  logs: BattleLog[];
  /** 最初のログが届くまで true */
  logsLoading: boolean;
  /** 全件のパースが終わるまで true */
  logsStreaming: boolean;
}

/**
 * バトルの再生画面と戦果サマリーを表示する。
 * ログの取得元を持たないため、履歴詳細と開発用ビューア（/dev/sim）で共用する。
 */
export default function BattleReplayPanel({
  battle,
  logs,
  logsLoading,
  logsStreaming,
}: BattleReplayPanelProps) {
  const [currentTimestamp, setCurrentTimestamp] = useState(0);
  // チャプタークリック由来のシークを明示するトークン。増分の度に BattleScene 側でカメラの
  // 再センタリングをトリガーする（自動再生・シークバードラッグでは増分しない、Issue #524）
  const [recenterToken, setRecenterToken] = useState(0);

  const handleChapterSeek = (timestamp: number) => {
    setCurrentTimestamp(timestamp);
    setRecenterToken((t) => t + 1);
  };

  const playerId = battle.player_info?.id ?? null;
  // battle.enemies_info のキャストをレンダーのたびに新しい配列参照として作ると、
  // useBattleChapters/BattleSummaryPanel 側の useMemo が毎回再計算されてしまうためメモ化する
  const enemies = useMemo(() => (battle.enemies_info ?? []) as MobileSuit[], [battle.enemies_info]);

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
    // BattleViewer は固定、戦果サマリーのみスクロール
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
                environment={getViewerEnvironment(battle)}
                theaterName={battle.theater_name}
                minovskyDensity={battle.minovsky_density}
                recenterToken={recenterToken}
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
              <ChapterTrack chapters={chapters} currentTimestamp={currentTimestamp} onSeek={handleChapterSeek} />
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
  );
}
