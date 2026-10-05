/* frontend/src/app/dev/sim/_components/SimReplay.tsx */
"use client";

import { useMemo } from "react";
import { LocalSimManifest } from "@/types/battle";
import {
  localSimBattleToResult,
  useLocalSimBattle,
  useLocalSimBattleLogs,
} from "@/services/api";
import ModalHeader from "@/components/history/ModalHeader";
import BattleReplayPanel from "@/components/history/BattleReplayPanel";

interface SimReplayProps {
  manifest: LocalSimManifest;
  index: number;
  onClose: () => void;
}

/** 1戦を履歴詳細と同じ部品で再生する。 */
export default function SimReplay({ manifest, index, onClose }: SimReplayProps) {
  const { battle, isError } = useLocalSimBattle(manifest.generation_id, index);
  const {
    logs,
    isLoading: logsLoading,
    isStreaming: logsStreaming,
    isError: logsError,
  } = useLocalSimBattleLogs(manifest.generation_id, index);
  const result = useMemo(
    () => (battle ? localSimBattleToResult(manifest, battle) : null),
    [manifest, battle]
  );

  if (isError || logsError) {
    return (
      <p className="text-red-400 text-sm" role="alert">
        バトルを読み込めませんでした: {String((isError ?? logsError)?.message ?? "")}
      </p>
    );
  }
  if (!result || !battle) {
    return <p className="text-gray-400 text-sm">バトルを読み込み中...</p>;
  }

  return (
    <div className="bg-gray-800 border border-green-800 rounded-lg flex flex-col">
      <ModalHeader battle={result} missionName={`${manifest.label} #${index}`} onClose={onClose} />
      <p className="px-4 pt-2 text-xs text-gray-500">
        seed {battle.seed} · {battle.steps_used} steps · {battle.elapsed_time.toFixed(1)}秒 ·{" "}
        {battle.log_count.toLocaleString()}件のログ
        {battle.timed_out && <span className="text-yellow-400"> · 最大ステップ数で打ち切り</span>}
      </p>
      <BattleReplayPanel
        battle={result}
        logs={logs ?? []}
        logsLoading={logsLoading}
        logsStreaming={logsStreaming}
      />
    </div>
  );
}
