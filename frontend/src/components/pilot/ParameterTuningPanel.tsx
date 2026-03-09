"use client";

import { useState } from "react";
import { Pilot } from "@/types/battle";
import { allocateStatusPoints } from "@/services/api";
import { KeyedMutator } from "swr";
import SciFiPanel from "@/components/ui/SciFiPanel";
import SciFiButton from "@/components/ui/SciFiButton";

/** ステータス値からランクを算出する（S/A/B/C/D の5段階） */
function getStatRank(value: number): string {
  if (value >= 20) return "S";
  if (value >= 15) return "A";
  if (value >= 10) return "B";
  if (value >= 5) return "C";
  return "D";
}

const STAT_RANK_COLORS: Record<string, string> = {
  S: "text-[#ff4444]",
  A: "text-[#ffb000]",
  B: "text-[#00ff41]",
  C: "text-[#00f0ff]",
  D: "text-gray-400",
};

const STATUS_LABELS: Record<string, { label: string; abbr: string; desc: string }> = {
  dex: { label: "器用", abbr: "DEX", desc: "命中・距離減衰緩和・被ダメージカット" },
  intel: { label: "直感", abbr: "INT", desc: "クリティカル率・回避率" },
  ref: { label: "反応", abbr: "REF", desc: "イニシアチブ・機動性ボーナス" },
  tou: { label: "耐久", abbr: "TOU", desc: "ダメージ加算・被クリティカル低下・防御加算" },
  luk: { label: "幸運", abbr: "LUK", desc: "ダメージ乱数偏り・完全回避" },
};

interface ParameterTuningPanelProps {
  pilot: Pilot;
  mutatePilot: KeyedMutator<Pilot>;
}

export default function ParameterTuningPanel({ pilot, mutatePilot }: ParameterTuningPanelProps) {
  const [pendingAlloc, setPendingAlloc] = useState<Record<string, number>>({
    dex: 0, intel: 0, ref: 0, tou: 0, luk: 0,
  });
  const [allocSaving, setAllocSaving] = useState(false);
  const [allocError, setAllocError] = useState<string>("");
  const [allocSuccess, setAllocSuccess] = useState<string>("");

  const totalPending = Object.values(pendingAlloc).reduce((s, v) => s + v, 0);
  const remainingPoints = pilot.status_points - totalPending;

  const pilotStatValues: Record<string, number> = {
    dex: pilot.dex,
    intel: pilot.intel,
    ref: pilot.ref,
    tou: pilot.tou,
    luk: pilot.luk,
  };

  const handleIncreaseStat = (stat: string) => {
    if (remainingPoints <= 0) return;
    setPendingAlloc((prev) => ({ ...prev, [stat]: prev[stat] + 1 }));
  };

  const handleDecreaseStat = (stat: string) => {
    if (pendingAlloc[stat] <= 0) return;
    setPendingAlloc((prev) => ({ ...prev, [stat]: prev[stat] - 1 }));
  };

  const handleSaveAllocation = async () => {
    if (totalPending === 0) return;
    setAllocSaving(true);
    setAllocError("");
    setAllocSuccess("");
    try {
      await allocateStatusPoints(pendingAlloc);
      setAllocSuccess("ステータスを保存しました");
      setPendingAlloc({ dex: 0, intel: 0, ref: 0, tou: 0, luk: 0 });
      await mutatePilot();
    } catch (err) {
      setAllocError(err instanceof Error ? err.message : "ステータスポイントの保存に失敗しました。もう一度お試しください");
    } finally {
      setAllocSaving(false);
    }
  };

  return (
    <SciFiPanel variant="secondary" className="p-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-5 border-b border-[#ffb000]/30 pb-3">
        <h2 className="text-sm font-bold tracking-widest text-[#ffb000] uppercase">
          PARAMETER TUNING
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">未割り振りポイント:</span>
          <span className={`text-xl font-bold ${remainingPoints > 0 ? "text-[#00ff41] drop-shadow-[0_0_6px_#00ff41]" : "text-gray-500"}`}>
            {remainingPoints}
          </span>
        </div>
      </div>

      {/* ステータス割り振りパネル */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-5">
        {(Object.keys(STATUS_LABELS) as Array<keyof typeof STATUS_LABELS>).map((stat) => {
          const info = STATUS_LABELS[stat];
          const currentVal = pilotStatValues[stat] ?? 0;
          const pendingVal = pendingAlloc[stat];
          const displayVal = currentVal + pendingVal;
          const rank = getStatRank(displayVal);
          const rankColor = STAT_RANK_COLORS[rank];

          return (
            <div
              key={stat}
              className="border border-[#ffb000]/30 bg-[#ffb000]/5 p-3 flex flex-col gap-2"
            >
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xl font-bold text-[#ffb000] uppercase">
                    {info.abbr}{" "}
                    <span className="text-gray-300 text-xs normal-case font-normal">/ {info.label}</span>
                  </p>
                  {/* ステータス説明, いったんコメントアウト */}
                  {/* <p className="text-xs text-gray-400 mt-0.5 leading-snug">{info.desc}</p> */}
                </div>
                <div className="text-right shrink-0 ml-2">
                  <p className="text-xl font-bold text-[#ffb000]">
                    <p className={`font-bold ${rankColor}`}>
                      Rank {rank}
                      ({displayVal})
                    </p>
                    {pendingVal > 0 && (
                      <span className="text-sm text-[#00ff41]"> (+{pendingVal})</span>
                    )}
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => handleDecreaseStat(stat)}
                  disabled={pendingVal <= 0}
                  className="flex-1 py-1.5 border border-[#ffb000]/50 bg-[#ffb000]/5 text-[#ffb000] text-sm font-bold
                    hover:border-[#ffb000] hover:bg-[#ffb000]/15
                    disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-[#ffb000]/5 disabled:hover:border-[#ffb000]/50
                    transition-colors"
                >
                  −
                </button>
                <button
                  onClick={() => handleIncreaseStat(stat)}
                  disabled={remainingPoints <= 0}
                  className="flex-1 py-1.5 border border-[#00ff41]/50 bg-[#00ff41]/5 text-[#00ff41] text-sm font-bold
                    hover:border-[#00ff41] hover:bg-[#00ff41]/15
                    disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-[#00ff41]/5 disabled:hover:border-[#00ff41]/50
                    transition-colors"
                >
                  ＋
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {allocError && (
        <p className="text-red-400 text-sm mb-2">{allocError}</p>
      )}
      {allocSuccess && (
        <p className="text-[#00ff41] text-sm mb-2">{allocSuccess}</p>
      )}

      <SciFiButton
        onClick={handleSaveAllocation}
        disabled={allocSaving || totalPending === 0}
        size="md"
        className="w-full sm:w-auto"
      >
        {allocSaving ? "SAVING..." : `SAVE PARAMETERS (${totalPending} pt)`}
      </SciFiButton>
    </SciFiPanel>
  );
}
