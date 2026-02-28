"use client";

import { useState, useCallback } from "react";
import { MobileSuit, Pilot } from "@/types/battle";
import { upgradeMobileSuit } from "@/services/api";
import { SciFiButton, SciFiPanel, SciFiProgress } from "@/components/ui";
import { getRankColor, getRank } from "@/utils/rankUtils";

/** ランク進捗計算用の閾値テーブル（rankUtils と同じ値） */
const RANK_PROGRESS_THRESHOLDS: Record<string, { rank: string; min: number }[]> = {
  hp: [
    { rank: "S", min: 2000 },
    { rank: "A", min: 1500 },
    { rank: "B", min: 1000 },
    { rank: "C", min: 700 },
    { rank: "D", min: 400 },
    { rank: "E", min: 0 },
  ],
  armor: [
    { rank: "S", min: 100 },
    { rank: "A", min: 80 },
    { rank: "B", min: 60 },
    { rank: "C", min: 40 },
    { rank: "D", min: 20 },
    { rank: "E", min: 0 },
  ],
  mobility: [
    { rank: "S", min: 2.0 },
    { rank: "A", min: 1.5 },
    { rank: "B", min: 1.2 },
    { rank: "C", min: 0.9 },
    { rank: "D", min: 0.6 },
    { rank: "E", min: 0.0 },
  ],
};

/** ランクキー → 表示ラベルのマッピング */
const RANK_KEY_LABELS: Record<string, string> = {
  hp_rank: "HP",
  armor_rank: "装甲",
  mobility_rank: "機動性",
};

type StatType =
  | "hp"
  | "armor"
  | "mobility"
  | "weapon_power"
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
  rankKey?: keyof Pick<MobileSuit, "hp_rank" | "armor_rank" | "mobility_rank">;
  rankStatName?: "hp" | "armor" | "mobility";
}

const STAT_TYPES: StatInfo[] = [
  {
    label: "HP",
    key: "hp",
    getValue: (ms) => ms.max_hp,
    format: (val) => val.toFixed(0),
    increment: 10,
    cap: 500,
    baseCost: 50,
    costDivisor: 200,
    rankKey: "hp_rank",
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
    rankKey: "armor_rank",
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
    rankKey: "mobility_rank",
    rankStatName: "mobility",
  },
  {
    label: "武器威力",
    key: "weapon_power",
    getValue: (ms) => {
      const weapon = ms.weapons && ms.weapons.length > 0 ? ms.weapons[0] : null;
      return weapon ? weapon.power : 0;
    },
    format: (val) => val.toFixed(0),
    increment: 2,
    cap: 200,
    baseCost: 80,
    costDivisor: 50,
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

/** ランク内の進捗率 (0–100) を計算 */
function calcRankProgress(
  statName: "hp" | "armor" | "mobility",
  value: number
): number {
  const table = RANK_PROGRESS_THRESHOLDS[statName];
  if (!table) return 0;

  // 現在のランク帯を特定
  let currentIdx = table.length - 1;
  for (let i = 0; i < table.length; i++) {
    if (value >= table[i].min) {
      currentIdx = i;
      break;
    }
  }

  const currentMin = table[currentIdx].min;
  // 最高ランク(S)なら進捗 100%
  if (currentIdx === 0) return 100;
  const nextMin = table[currentIdx - 1].min;
  return Math.min(100, ((value - currentMin) / (nextMin - currentMin)) * 100);
}

interface StatusTabProps {
  mobileSuit: MobileSuit;
  pilot: Pilot | undefined;
  onUpgraded: (updatedMs: MobileSuit) => void;
}

export default function StatusTab({ mobileSuit, pilot, onUpgraded }: StatusTabProps) {
  const [pendingSteps, setPendingSteps] = useState<Record<string, number>>({});
  const [confirming, setConfirming] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const getSteps = (key: string) => pendingSteps[key] ?? 0;

  const setSteps = useCallback((key: string, steps: number) => {
    setPendingSteps((prev) => ({ ...prev, [key]: steps }));
  }, []);

  // 全ステータスの合計確定コスト（クレジット表示用）
  const totalPendingCost = STAT_TYPES.reduce((sum, stat) => {
    const steps = getSteps(stat.key);
    if (steps === 0) return sum;
    const currentValue = stat.getValue(mobileSuit);
    return sum + simulateSteps(stat, currentValue, steps).totalCost;
  }, 0);

  const handleConfirm = async (stat: StatInfo) => {
    const steps = getSteps(stat.key);
    if (!pilot || steps === 0) return;

    setConfirming(stat.key);
    setMessage(null);

    try {
      const response = await upgradeMobileSuit({
        mobile_suit_id: mobileSuit.id,
        target_stat: stat.key,
        steps,
      });

      setMessage(
        `✓ ${stat.label} を ${steps} 段階強化しました！ (コスト: ${response.cost_paid.toLocaleString()} Credits)`
      );
      setSteps(stat.key, 0);
      onUpgraded(response.mobile_suit);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      setMessage(`✗ エラー: ${errorMessage}`);
    } finally {
      setConfirming(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* 基本スペック表示（ランク表記） */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {(["hp_rank", "armor_rank", "mobility_rank"] as const).map((rankKey) => {
          return (
            <div
              key={rankKey}
              className="p-3 bg-[#0a0a0a] rounded border border-[#00ff41]/30"
            >
              <div className="text-xs text-[#00ff41]/60">{RANK_KEY_LABELS[rankKey]}</div>
              <div
                className={`text-lg font-bold ${getRankColor(
                  mobileSuit[rankKey] ?? "C"
                )}`}
              >
                {mobileSuit[rankKey] ?? "C"}
              </div>
            </div>
          );
        })}
        <div className="p-3 bg-[#0a0a0a] rounded border border-[#00ff41]/30">
          <div className="text-xs text-[#00ff41]/60">武器威力</div>
          <div className="text-lg font-bold text-[#00ff41]">
            {mobileSuit.weapons?.[0]?.power ?? 0}
          </div>
        </div>
      </div>

      {/* 所持金 */}
      {pilot && (
        <div className="p-3 bg-[#0a0a0a] rounded border border-[#ffb000]/30">
          <span className="text-[#ffb000]/60 text-sm">所持金: </span>
          <span className="text-[#ffb000] font-bold">
            {pilot.credits.toLocaleString()} Credits
          </span>
          {totalPendingCost > 0 && (
            <span className="ml-2 text-sm text-[#00f0ff]">
              (確定後残高: {(pilot.credits - totalPendingCost).toLocaleString()})
            </span>
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
      <div className="space-y-3">
        <h4 className="text-sm font-bold text-[#00f0ff] uppercase tracking-wider">
          ステータス強化 (Engineering)
        </h4>

        {STAT_TYPES.map((stat) => {
          const steps = getSteps(stat.key);
          const currentValue = stat.getValue(mobileSuit);
          const isMaxed = currentValue >= stat.cap;
          const maxAffordable = pilot
            ? calcMaxAffordableSteps(stat, currentValue, pilot.credits)
            : 0;

          const { totalCost, finalValue } = simulateSteps(stat, currentValue, steps);

          const currentRank = stat.rankKey ? mobileSuit[stat.rankKey] : undefined;
          const previewRank =
            stat.rankStatName && steps > 0
              ? getRank(stat.rankStatName, finalValue)
              : undefined;
          const isRankUp =
            !!currentRank && !!previewRank && previewRank !== currentRank;

          // ランク内進捗バー
          const rankProgress = stat.rankStatName
            ? calcRankProgress(stat.rankStatName, currentValue)
            : null;
          const previewRankProgress =
            stat.rankStatName && steps > 0
              ? calcRankProgress(stat.rankStatName, finalValue)
              : null;

          const canAfford = pilot ? pilot.credits >= totalCost : false;

          return (
            <div
              key={stat.key}
              className="p-4 bg-[#0a0a0a] rounded border border-[#00ff41]/20"
            >
              {/* ラベル行 */}
              <h5 className="text-sm font-bold mb-2 text-[#00ff41]">{stat.label}</h5>

              {/* 現在値 → 強化後値 */}
              <div className="flex flex-wrap items-center gap-2 text-sm mb-2">
                {currentRank ? (
                  <span>
                    現在:{" "}
                    <span className={`font-bold ${getRankColor(currentRank)}`}>
                      [{currentRank}]
                    </span>
                  </span>
                ) : (
                  <span>
                    現在:{" "}
                    <span className="text-[#ffb000] font-bold">
                      {stat.format(currentValue)}
                    </span>
                  </span>
                )}

                {steps > 0 && (
                  <>
                    <span className="text-[#00ff41]/50">▶</span>
                    {previewRank ? (
                      <span>
                        強化後:{" "}
                        <span
                          className={`font-bold ${getRankColor(previewRank)}`}
                        >
                          [{previewRank}]
                        </span>
                      </span>
                    ) : (
                      <span>
                        強化後:{" "}
                        <span className="text-[#00ff41] font-bold">
                          {stat.format(finalValue)}
                        </span>
                      </span>
                    )}
                  </>
                )}
              </div>

              {/* ランク進捗バー */}
              {rankProgress !== null && (
                <SciFiProgress
                  value={
                    steps > 0 && previewRankProgress !== null
                      ? previewRankProgress
                      : rankProgress
                  }
                  isRankUp={isRankUp}
                  className="mb-3"
                />
              )}

              {isMaxed ? (
                <SciFiButton variant="secondary" size="sm" disabled>
                  最大値
                </SciFiButton>
              ) : (
                <>
                  {/* ステップ操作ボタン群（レスポンシブ） */}
                  <div className="flex flex-col md:flex-row gap-2 md:items-center mb-2">
                    <div className="flex gap-1">
                      {/* << リセット */}
                      <button
                        onClick={() => setSteps(stat.key, 0)}
                        disabled={steps === 0}
                        className="touch-manipulation min-w-[44px] min-h-[44px] flex-1 md:flex-none md:w-11 font-mono font-bold text-xs border border-[#00ff41]/40 text-[#00ff41]/70 bg-[#050505] hover:bg-[#00ff41]/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        aria-label={`${stat.label} ステップをリセット`}
                      >
                        {"<<"}
                      </button>
                      {/* < -1 */}
                      <button
                        onClick={() => setSteps(stat.key, Math.max(0, steps - 1))}
                        disabled={steps === 0}
                        className="touch-manipulation min-w-[44px] min-h-[44px] flex-1 md:flex-none md:w-11 font-mono font-bold text-xs border border-[#00ff41]/40 text-[#00ff41]/70 bg-[#050505] hover:bg-[#00ff41]/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        aria-label={`${stat.label} ステップを1減らす`}
                      >
                        {"<"}
                      </button>
                      {/* > +1 */}
                      <button
                        onClick={() =>
                          setSteps(
                            stat.key,
                            Math.min(maxAffordable, steps + 1)
                          )
                        }
                        disabled={steps >= maxAffordable}
                        className="touch-manipulation min-w-[44px] min-h-[44px] flex-1 md:flex-none md:w-11 font-mono font-bold text-xs border border-[#00ff41]/40 text-[#00ff41]/70 bg-[#050505] hover:bg-[#00ff41]/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        aria-label={`${stat.label} ステップを1増やす`}
                      >
                        {">"}
                      </button>
                      {/* >> 最大 */}
                      <button
                        onClick={() => setSteps(stat.key, maxAffordable)}
                        disabled={steps >= maxAffordable}
                        className="touch-manipulation min-w-[44px] min-h-[44px] flex-1 md:flex-none md:w-11 font-mono font-bold text-xs border border-[#00ff41]/40 text-[#00ff41]/70 bg-[#050505] hover:bg-[#00ff41]/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        aria-label={`${stat.label} ステップを最大にする`}
                      >
                        {">>"}
                      </button>
                    </div>

                    {/* ステップ数・コスト表示 */}
                    <div className="text-xs text-[#00ff41]/60 flex-1">
                      {steps > 0 ? (
                        <>
                          <span className="text-[#00ff41] font-bold">
                            {steps} 段階
                          </span>
                          {" / "}
                          <span className={canAfford ? "text-[#ffb000]" : "text-red-400"}>
                            {totalCost.toLocaleString()} Credits
                          </span>
                        </>
                      ) : (
                        <span>段階を選択してください</span>
                      )}
                    </div>
                  </div>

                  {/* 確定ボタン */}
                  <SciFiButton
                    variant="primary"
                    size="sm"
                    className="w-full touch-manipulation"
                    onClick={() => handleConfirm(stat)}
                    disabled={
                      steps === 0 ||
                      !canAfford ||
                      confirming === stat.key
                    }
                  >
                    {confirming === stat.key
                      ? "強化中..."
                      : steps > 0
                      ? `実行 (${totalCost.toLocaleString()} Credits)`
                      : "実行"}
                  </SciFiButton>
                </>
              )}
            </div>
          );
        })}
      </div>

      {/* 詳細スペック */}
      <SciFiPanel variant="primary" chiseled={false}>
        <div className="p-4">
          <h4 className="text-sm font-bold text-[#00ff41] mb-3 uppercase tracking-wider">
            戦闘適性
          </h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-[#00ff41]/60">格闘適性:</span>
              <span className="ml-2 font-bold text-red-400">
                ×{(mobileSuit.melee_aptitude ?? 1.0).toFixed(1)}
              </span>
            </div>
            <div>
              <span className="text-[#00ff41]/60">射撃適性:</span>
              <span className="ml-2 font-bold text-blue-400">
                ×{(mobileSuit.shooting_aptitude ?? 1.0).toFixed(1)}
              </span>
            </div>
            <div>
              <span className="text-[#00ff41]/60">命中補正:</span>
              <span className="ml-2 font-bold text-[#00ff41]">
                {(mobileSuit.accuracy_bonus ?? 0.0) >= 0 ? "+" : ""}
                {(mobileSuit.accuracy_bonus ?? 0.0).toFixed(1)}%
              </span>
            </div>
            <div>
              <span className="text-[#00ff41]/60">回避補正:</span>
              <span className="ml-2 font-bold text-[#ffb000]">
                {(mobileSuit.evasion_bonus ?? 0.0) >= 0 ? "+" : ""}
                {(mobileSuit.evasion_bonus ?? 0.0).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      </SciFiPanel>
    </div>
  );
}
