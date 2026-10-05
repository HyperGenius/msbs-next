/* frontend/src/components/history/BattleDetailModal.tsx */
"use client";

import { BattleResult } from "@/types/battle";
import ModalHeader from "./ModalHeader";
import BattleReplayPanel from "./BattleReplayPanel";
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
  // バトルログを遅延ロード（リプレイ用）。全件ダウンロード完了を待たず、
  // 届いた分から段階的に反映する（Issue #494）。isLoadingは初回データ到達まで、
  // isStreamingは全件パース完了までtrueになる
  const { logs: fetchedLogs, isLoading: logsLoading, isStreaming: logsStreaming } = useBattleLogs(battle.id);

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
        <BattleReplayPanel
          battle={battle}
          logs={fetchedLogs ?? []}
          logsLoading={logsLoading}
          logsStreaming={logsStreaming}
        />
      </div>
    </div>
  );
}
