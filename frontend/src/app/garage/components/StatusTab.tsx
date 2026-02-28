"use client";

import { useState, useMemo, useCallback } from "react";
import { MobileSuit, Pilot } from "@/types/battle";
import { bulkUpgradeMobileSuit } from "@/services/api";
import { SciFiBlockIndicator } from "@/components/ui";
import HoldSciFiButton from "@/components/ui/HoldSciFiButton";
import { getRankColor, getRank } from "@/utils/rankUtils";

type StatType =
  | "hp"
  | "armor"
  | "mobility"
  | "melee_aptitude"
  | "shooting_aptitude"
  | "accuracy_bonus"
  | "evasion_bonus"
  | "acceleration_bonus"
  | "turning_bonus";

interface StatInfo {
  label: string;
  key: StatType;
  getValue: (ms: MobileSuit) => number;
  format: (val: number) => string;
  increment: number;
  cap: number;
  baseCost: number;
  costDivisor: number;
  rankStatName?: "hp" | "armor" | "mobility";
}

const STAT_TYPES: StatInfo[] = [
  {
    label: "耐久",
    key: "hp",
    getValue: (ms) => ms.max_hp,
    format: (val) => val.toFixed(0),
    increment: 10,
    cap: 500,
    baseCost: 50,
    costDivisor: 200,
    rankStatName: "hp",
  },
  {
    label: "装甲",
    key: "armor",
    getValue: (ms) => ms.armor,
    format: (val) => val.toFixed(0),
    increment: 1,
    cap: 50,
    baseCost: 100,
    costDivisor: 10,
    rankStatName: "armor",
  },
  {
    label: "機動性",
    key: "mobility",
    getValue: (ms) => ms.mobility,
    format: (val) => val.toFixed(2),
    increment: 0.05,
    cap: 3.0,
    baseCost: 150,
    costDivisor: 2,
    rankStatName: "mobility",
  },
  {
    label: "格闘適性",
    key: "melee_aptitude",
    getValue: (ms) => ms.melee_aptitude ?? 1.0,
    format: (val) => `×${val.toFixed(2)}`,
    increment: 0.05,
    cap: 2.0,
    baseCost: 200,
    costDivisor: 2,
  },
  {
    label: "射撃適性",
    key: "shooting_aptitude",
    getValue: (ms) => ms.shooting_aptitude ?? 1.0,
    format: (val) => `×${val.toFixed(2)}`,
    increment: 0.05,
    cap: 2.0,
    baseCost: 200,
    costDivisor: 2,
  },
  {
    label: "命中補正",
    key: "accuracy_bonus",
    getValue: (ms) => ms.accuracy_bonus ?? 0.0,
    format: (val) => `${val >= 0 ? "+" : ""}${val.toFixed(1)}%`,
    increment: 0.5,
    cap: 10.0,
    baseCost: 120,
    costDivisor: 10,
  },
  {
    label: "回避補正",
    key: "evasion_bonus",
    getValue: (ms) => ms.evasion_bonus ?? 0.0,
    format: (val) => `${val >= 0 ? "+" : ""}${val.toFixed(1)}%`,
    increment: 0.5,
    cap: 10.0,
    baseCost: 120,
    costDivisor: 10,
  },
  {
    label: "加速補正",
    key: "acceleration_bonus",
    getValue: (ms) => ms.acceleration_bonus ?? 0.0,
    format: (val) => `${val >= 0 ? "+" : ""}${val.toFixed(2)}`,
    increment: 0.05,
    cap: 2.0,
    baseCost: 130,
    costDivisor: 2,
  },
  {
    label: "旋回補正",
    key: "turning_bonus",
    getValue: (ms) => ms.turning_bonus ?? 0.0,
    format: (val) => `${val >= 0 ? "+" : ""}${val.toFixed(2)}`,
    increment: 0.05,
    cap: 2.0,
    baseCost: 130,
    costDivisor: 2,
  },
];

/** バックエンドと同じコスト計算式 */
function calcStepCost(stat: StatInfo, value: number): number {
  return Math.floor(stat.baseCost * (1 + value / stat.costDivisor));
}

/** N ステップ分の累積コストとシミュレーション後の値を計算 */
function simulateSteps(
  stat: StatInfo,
  currentValue: number,
  steps: number
): { totalCost: number; finalValue: number } {
  let value = currentValue;
  let totalCost = 0;
  for (let i = 0; i < steps; i++) {
    if (value >= stat.cap) break;
    totalCost += calcStepCost(stat, value);
    value = Math.min(value + stat.increment, stat.cap);
  }
  return { totalCost, finalValue: value };
}

/** 所持クレジットで何ステップ踏めるか（上限: cap まで）を計算 */
function calcMaxAffordableSteps(
  stat: StatInfo,
  currentValue: number,
  credits: number
): number {
  let value = currentValue;
  let remaining = credits;
  let steps = 0;
  while (value < stat.cap) {
    const cost = calcStepCost(stat, value);
    if (remaining < cost) break;
    remaining -= cost;
    value = Math.min(value + stat.increment, stat.cap);
    steps++;
  }
  return steps;
}

/**
 * ランク文字列をすべてのステータスについて計算する。
 * rankStatName がある場合は getRank() を使用し、
 * ない場合はキャップ比率からランクを算出する。
 */
function getRankString(stat: StatInfo, value: number): string {
  if (stat.rankStatName) {
    return getRank(stat.rankStatName, value);
  }
  const pct = stat.cap > 0 ? value / stat.cap : 0;
  if (pct >= 0.9) return "S";
  if (pct >= 0.7) return "A";
  if (pct >= 0.5) return "B";
  if (pct >= 0.3) return "C";
  return "D";
}

interface StatusTabProps {
  mobileSuit: MobileSuit;
  pilot: Pilot | undefined;
  onUpgraded: (updatedMs: MobileSuit) => void;
}

export default function StatusTab({ mobileSuit, pilot, onUpgraded }: StatusTabProps) {
  const [pendingSteps, setPendingSteps] = useState<Record<string, number>>({});
  const [isApplying, setIsApplying] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const getSteps = (key: string) => pendingSteps[key] ?? 0;

  const setSteps = useCallback((key: string, steps: number) => {
    setPendingSteps((prev) => ({ ...prev, [key]: steps }));
  }, []);

  /** 全ステータスの合計確定コスト */
  const totalPendingCost = useMemo(() => {
    return STAT_TYPES.reduce((sum, stat) => {
      const steps = pendingSteps[stat.key] ?? 0;
      if (steps === 0) return sum;
      const currentValue = stat.getValue(mobileSuit);
      return sum + simulateSteps(stat, currentValue, steps).totalCost;
    }, 0);
  }, [pendingSteps, mobileSuit]);

  const hasPendingUpgrades = totalPendingCost > 0;
  const canAffordAll = pilot ? pilot.credits >= totalPendingCost : false;

  const handleApplyAll = async () => {
    if (!pilot || !hasPendingUpgrades || !canAffordAll) return;

    const upgrades: Record<string, number> = {};
    for (const stat of STAT_TYPES) {
      const steps = getSteps(stat.key);
      if (steps > 0) upgrades[stat.key] = steps;
    }

    setIsApplying(true);
    setMessage(null);

    try {
      const response = await bulkUpgradeMobileSuit({
        mobile_suit_id: mobileSuit.id,
        upgrades,
      });

      setMessage(
        `✓ 強化完了！ (合計コスト: ${response.total_cost_paid.toLocaleString()} Credits)`
      );
      setPendingSteps({});
      onUpgraded(response.mobile_suit);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      setMessage(`✗ エラー: ${errorMessage}`);
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 所持金（現在 ➔ 変更後） */}
      {pilot && (
        <div className="p-3 bg-[#0a0a0a] rounded border border-[#ffb000]/30 text-sm">
          <span className="text-[#ffb000]">💰 所持金: </span>
          <span className="text-[#ffb000] font-bold">
            {pilot.credits.toLocaleString()} Credits
          </span>
          {hasPendingUpgrades && (
            <>
              <span className="text-[#ffb000]/60"> ➔ </span>
              <span
                className={`font-bold ${
                  canAffordAll ? "text-[#00f0ff]" : "text-red-400"
                }`}
              >
                {(pilot.credits - totalPendingCost).toLocaleString()} Credits
              </span>
            </>
          )}
        </div>
      )}

      {/* メッセージ */}
      {message && (
        <div
          className={`p-3 rounded border text-sm ${
            message.startsWith("✓")
              ? "bg-[#00ff41]/10 border-[#00ff41]/50 text-[#00ff41]"
              : "bg-red-900/30 border-red-600/50 text-red-300"
          }`}
        >
          {message}
        </div>
      )}

      {/* 強化パネル */}
      <div className="divide-y divide-[#00ff41]/10">
        {STAT_TYPES.map((stat) => {
          const steps = getSteps(stat.key);
          const currentValue = stat.getValue(mobileSuit);
          const isMaxed = currentValue >= stat.cap;
          const maxAffordable = pilot
            ? calcMaxAffordableSteps(stat, currentValue, pilot.credits)
            : 0;

          const { totalCost: stepsCost, finalValue } = simulateSteps(stat, currentValue, steps);

          const currentRank = getRankString(stat, currentValue);
          const previewRank = steps > 0 ? getRankString(stat, finalValue) : null;
          const isRankUp = !!previewRank && previewRank !== currentRank;

          // 現在の1回分のコスト（[-]/[+]横に表示）
          const nextStepCost = isMaxed ? 0 : calcStepCost(stat, currentValue + steps * stat.increment);

          return (
            <div key={stat.key} className="py-4 first:pt-0">
              {/* ラベル行 */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-[#00ff41] uppercase tracking-wider">
                  {stat.label}
                </span>
                <span className={`text-xs text-[#ffb000] ${steps > 0 ? "visible" : "invisible"}`}>
                  {/* {stepsCost > 0 ? `${stepsCost.toLocaleString()} CR` : "0 CR"} */}
                  Credits: {stepsCost.toLocaleString()} CR
                </span>
              </div>

              {/* ランク + ブロックインジケーター + ボタン行 */}
              <div className="flex items-center gap-2 flex-wrap">
                {/* ランクバッジ */}
                <div className="flex items-center gap-1.5 w-[6.5rem] shrink-0">
                  <span
                    className={`text-base font-bold font-mono border px-1.5 py-0.5 ${
                      isRankUp
                        ? `${getRankColor(previewRank!)} border-current`
                        : `${getRankColor(currentRank)} border-current/40`
                    }`}
                  >
                    {isRankUp ? previewRank : currentRank}
                  </span>
                  <span
                    className={`text-[#00f0ff] text-xs font-bold animate-pulse whitespace-nowrap ${
                      isRankUp ? "visible" : "invisible"
                    }`}
                  >
                    ✨RANK UP!
                  </span>
                </div>

                {/* ブロックインジケーター */}
                <SciFiBlockIndicator
                  currentValue={currentValue}
                  cap={stat.cap}
                  pendingSteps={steps}
                  increment={stat.increment}
                  className="flex-1"
                />

                {/* [-] [+] ボタンと1ステップコスト */}
                {isMaxed ? (
                  <span className="text-xs text-[#00ff41]/40 font-mono">MAX</span>
                ) : (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setSteps(stat.key, Math.max(0, steps - 1))}
                      disabled={steps === 0}
                      className="touch-manipulation w-8 h-8 font-mono font-bold text-sm border border-[#00ff41]/40 text-[#00ff41] bg-[#050505] hover:bg-[#00ff41]/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      aria-label={`${stat.label} ステップを1減らす`}
                    >
                      −
                    </button>
                    <span className="w-5 text-center text-xs font-mono text-[#00ff41]/70">
                      {steps}
                    </span>
                    <button
                      onClick={() =>
                        setSteps(stat.key, Math.min(maxAffordable, steps + 1))
                      }
                      disabled={steps >= maxAffordable}
                      className="touch-manipulation w-8 h-8 font-mono font-bold text-sm border border-[#00ff41]/40 text-[#00ff41] bg-[#050505] hover:bg-[#00ff41]/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      aria-label={`${stat.label} ステップを1増やす`}
                    >
                      ＋
                    </button>
                    <span className={`text-xs text-[#00ff41]/40 font-mono ml-1 w-16 text-right`}>
                      {nextStepCost > 0 ? `${nextStepCost} CR` : ""}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 一括適用ボタン */}
      <div className="pt-2 border-t border-[#00ff41]/20">
        <HoldSciFiButton
          onHoldComplete={handleApplyAll}
          disabled={!hasPendingUpgrades || !canAffordAll}
          loading={isApplying}
          label={
            hasPendingUpgrades
              ? `長押しで確定 (合計: ${totalPendingCost.toLocaleString()} Credits)`
              : "長押しで確定"
          }
          loadingLabel="強化中..."
        />
      </div>
    </div>
  );
}
