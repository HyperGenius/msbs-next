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
import { getObjectiveSummary, OBJECTIVE_STATUS_LABELS } from "@/utils/missionName";
import SimDebugPanel from "./SimDebugPanel";

interface SimReplayProps {
  manifest: LocalSimManifest;
  index: number;
  onClose: () => void;
}

/** 1戦を履歴詳細と同じ部品で再生し、選んだ機体の AI の判断を再生位置に合わせて表示する。 */
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
  const units = useMemo(() => (battle ? [battle.player_info, ...battle.enemies_info] : []), [battle]);
  // 作戦の戦闘だけ作戦の結果が入る。作戦の無い戦闘は null
  const objective = result ? getObjectiveSummary(result) : null;

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
      <ModalHeader
        battle={result}
        missionName={`${battle.mission_name ? `${battle.mission_name} · ` : ""}${manifest.label} #${index}`}
        onClose={onClose}
      />
      {objective && (
        <p className="px-4 pt-2 text-sm">
          <span
            className={`font-bold ${
              objective.status === "SUCCESS"
                ? "text-green-300"
                : objective.status === "FAILURE"
                  ? "text-red-400"
                  : "text-yellow-300"
            }`}
          >
            {OBJECTIVE_STATUS_LABELS[objective.status]}
          </span>
          {objective.total ? (
            <span className="text-gray-400 ml-2">
              離脱 {objective.progress ?? 0}/{objective.total}
              {objective.required ? `（必要 ${objective.required}）` : ""}
              {objective.lost ? ` · 撃破された友軍 ${objective.lost}機` : ""}
            </span>
          ) : null}
        </p>
      )}
      <p className="px-4 pt-2 text-xs text-gray-500">
        {manifest.source === "production" ? "本番の戦闘" : `seed ${battle.seed}`} · {battle.steps_used}{" "}
        steps · {battle.elapsed_time.toFixed(1)}秒 ·{" "}
        {battle.log_count.toLocaleString()}件のログ
        {battle.timed_out && <span className="text-yellow-400"> · 最大ステップ数で打ち切り</span>}
      </p>
      <BattleReplayPanel
        battle={result}
        logs={logs ?? []}
        logsLoading={logsLoading}
        logsStreaming={logsStreaming}
        renderTimelinePanel={(currentTimestamp) => (
          <SimDebugPanel
            generationId={manifest.generation_id}
            index={index}
            units={units}
            currentTimestamp={currentTimestamp}
          />
        )}
      />
    </div>
  );
}
