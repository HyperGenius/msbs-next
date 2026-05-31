"use client";

import { useState } from "react";
import { Pilot } from "@/types/battle";
import { allocateStatusPoints } from "@/services/api";
import { KeyedMutator } from "swr";
import SciFiPanel from "@/components/ui/SciFiPanel";
import SciFiButton from "@/components/ui/SciFiButton";
import StatusRadarChart, { StatKey } from "./StatusRadarChart";
import StatusStatCard from "./StatusStatCard";
import StatusPointGauge from "./StatusPointGauge";

interface ParameterTuningPanelProps {
  pilot: Pilot;
  mutatePilot: KeyedMutator<Pilot>;
}

/** 表示するステータスキーの順序 */
const STAT_ORDER: StatKey[] = ["sht", "mel", "intel", "ref", "tou", "luk"];

/**
 * パイロットのステータスポイント割り振り画面。
 * 左ペイン: レーダーチャート + ポイントゲージ
 * 右ペイン: 2列グリッドのステータスカード
 * モバイル（lg未満）: 単列縦積みにフォールバック
 */
export default function ParameterTuningPanel({ pilot, mutatePilot }: ParameterTuningPanelProps) {
  const [pendingAlloc, setPendingAlloc] = useState<Record<StatKey, number>>({
    sht: 0, mel: 0, intel: 0, ref: 0, tou: 0, luk: 0,
  });
  const [allocSaving, setAllocSaving] = useState(false);
  const [allocError, setAllocError] = useState<string>("");
  const [allocSuccess, setAllocSuccess] = useState<string>("");

  const totalPending = Object.values(pendingAlloc).reduce((s, v) => s + v, 0);
  const remainingPoints = pilot.status_points - totalPending;

  /** 各ステータスの現在値をまとめたオブジェクト */
  const pilotStatValues: Record<StatKey, number> = {
    sht: pilot.sht,
    mel: pilot.mel,
    intel: pilot.intel,
    ref: pilot.ref,
    tou: pilot.tou,
    luk: pilot.luk,
  };

  const handleIncreaseStat = (stat: StatKey) => {
    if (remainingPoints <= 0) return;
    setPendingAlloc((prev) => ({ ...prev, [stat]: prev[stat] + 1 }));
  };

  const handleDecreaseStat = (stat: StatKey) => {
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
      setPendingAlloc({ sht: 0, mel: 0, intel: 0, ref: 0, tou: 0, luk: 0 });
      await mutatePilot();
    } catch (err) {
      setAllocError(err instanceof Error ? err.message : "ステータスポイントの保存に失敗しました。もう一度お試しください");
    } finally {
      setAllocSaving(false);
    }
  };

  return (
    <SciFiPanel variant="secondary" className="p-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between mb-5 border-b border-[#ffb000]/30 pb-3">
        <h2 className="text-sm font-bold tracking-widest text-[#ffb000] uppercase">
          PARAMETER TUNING
        </h2>
      </div>

      {/* メインコンテンツ: lg以上で2ペイン、lg未満で縦積み */}
      <div className="flex flex-col lg:flex-row gap-5 mb-5">
        {/* 左ペイン: レーダーチャート + ポイントゲージ */}
        <div className="flex flex-col gap-4 lg:w-2/5">
          {/* レーダーチャート */}
          <div className="border border-[#ffb000]/20 bg-[#ffb000]/3 p-2" style={{ height: 240 }}>
            <StatusRadarChart
              current={pilotStatValues}
              pending={pendingAlloc}
            />
          </div>

          {/* ポイントゲージ */}
          <StatusPointGauge
            total={pilot.status_points}
            remaining={remainingPoints}
          />
        </div>

        {/* 右ペイン: ステータスカード（2列グリッド） */}
        <div className="lg:w-3/5 grid grid-cols-2 gap-3">
          {STAT_ORDER.map((stat) => (
            <StatusStatCard
              key={stat}
              stat={stat}
              currentValue={pilotStatValues[stat]}
              pending={pendingAlloc[stat]}
              remainingPoints={remainingPoints}
              onIncrease={() => handleIncreaseStat(stat)}
              onDecrease={() => handleDecreaseStat(stat)}
            />
          ))}
        </div>
      </div>

      {/* フィードバックメッセージ */}
      {allocError && (
        <p className="text-red-400 text-sm mb-2">{allocError}</p>
      )}
      {allocSuccess && (
        <p className="text-[#00ff41] text-sm mb-2">{allocSuccess}</p>
      )}

      {/* 保存ボタン */}
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
