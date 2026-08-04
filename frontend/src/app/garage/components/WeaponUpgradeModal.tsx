/* frontend/src/app/garage/components/WeaponUpgradeModal.tsx */
"use client";

import { useMemo, useState } from "react";
import { PlayerWeapon, Pilot, WeaponUpgradeStatType } from "@/types/battle";
import { upgradePlayerWeapon } from "@/services/api";
import SciFiModal from "@/components/ui/SciFiModal";
import { SciFiBlockIndicator, SciFiHeading } from "@/components/ui";
import HoldSciFiButton from "@/components/ui/HoldSciFiButton";
import { getRankColor, getWeaponRank } from "@/utils/rankUtils";

interface WeaponUpgradeModalProps {
  playerWeapon: PlayerWeapon;
  pilot: Pilot | undefined;
  onClose: () => void;
  /** 改造成功時に呼ばれる（更新後の PlayerWeapon を渡す） */
  onUpgraded: (updated: PlayerWeapon) => void;
}

interface WeaponStatInfo {
  label: string;
  key: WeaponUpgradeStatType;
  rankStatName: "weapon_power" | "weapon_accuracy";
  getBase: (pw: PlayerWeapon) => number;
  getBonus: (pw: PlayerWeapon) => number;
  increment: number;
  /** 実効値(base+bonus)がこの倍率(base × capMultiplier)に達するまで改造可能 */
  capMultiplier: number;
  baseCost: number;
  costDivisor: number;
}

// バックエンド(WeaponEngineeringService)の _STAT_CONFIGS と同じ定義
const STAT_TYPES: WeaponStatInfo[] = [
  {
    label: "威力",
    key: "power_bonus",
    rankStatName: "weapon_power",
    getBase: (pw) => (pw.base_snapshot as { power?: number }).power ?? 0,
    getBonus: (pw) => pw.custom_stats?.power_bonus ?? 0,
    increment: 5,
    capMultiplier: 2.0,
    baseCost: 60,
    costDivisor: 30,
  },
  {
    label: "命中率",
    key: "accuracy_bonus",
    rankStatName: "weapon_accuracy",
    getBase: (pw) => (pw.base_snapshot as { accuracy?: number }).accuracy ?? 0,
    getBonus: (pw) => pw.custom_stats?.accuracy_bonus ?? 0,
    increment: 1.0,
    capMultiplier: 1.3,
    baseCost: 100,
    costDivisor: 5,
  },
];

/** バックエンドと同じコスト計算式（ボーナス値ベース） */
function calcStepCost(stat: WeaponStatInfo, bonus: number): number {
  return Math.floor(stat.baseCost * (1 + bonus / stat.costDivisor));
}

/** ボーナス値の上限（実効値が base × capMultiplier に達するまで） */
function bonusCap(stat: WeaponStatInfo, base: number): number {
  return base * (stat.capMultiplier - 1);
}

/** N ステップ分の累積コストとシミュレーション後のボーナス値を計算 */
function simulateSteps(
  stat: WeaponStatInfo,
  base: number,
  currentBonus: number,
  steps: number
): { totalCost: number; finalBonus: number } {
  const cap = bonusCap(stat, base);
  let bonus = currentBonus;
  let totalCost = 0;
  for (let i = 0; i < steps; i++) {
    if (bonus >= cap) break;
    totalCost += calcStepCost(stat, bonus);
    bonus = Math.min(bonus + stat.increment, cap);
  }
  return { totalCost, finalBonus: bonus };
}

/** 所持クレジットで何ステップ踏めるか（上限: cap まで）を計算 */
function calcMaxAffordableSteps(
  stat: WeaponStatInfo,
  base: number,
  currentBonus: number,
  credits: number
): number {
  const cap = bonusCap(stat, base);
  let bonus = currentBonus;
  let remaining = credits;
  let steps = 0;
  while (bonus < cap) {
    const cost = calcStepCost(stat, bonus);
    if (remaining < cost) break;
    remaining -= cost;
    bonus = Math.min(bonus + stat.increment, cap);
    steps++;
  }
  return steps;
}

export default function WeaponUpgradeModal({
  playerWeapon,
  pilot,
  onClose,
  onUpgraded,
}: WeaponUpgradeModalProps) {
  const [pendingSteps, setPendingSteps] = useState<Record<string, number>>({});
  const [isApplying, setIsApplying] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const spec = playerWeapon.base_snapshot as { name?: string; type?: string };

  const getSteps = (key: string) => pendingSteps[key] ?? 0;
  const setSteps = (key: string, steps: number) =>
    setPendingSteps((prev) => ({ ...prev, [key]: steps }));

  /** 全ステータスの合計確定コスト */
  const totalPendingCost = useMemo(() => {
    return STAT_TYPES.reduce((sum, stat) => {
      const steps = pendingSteps[stat.key] ?? 0;
      if (steps === 0) return sum;
      const base = stat.getBase(playerWeapon);
      const bonus = stat.getBonus(playerWeapon);
      return sum + simulateSteps(stat, base, bonus, steps).totalCost;
    }, 0);
  }, [pendingSteps, playerWeapon]);

  const hasPendingUpgrades = totalPendingCost > 0;
  const canAffordAll = pilot ? pilot.credits >= totalPendingCost : false;

  // 武器改造には bulk エンドポイントが無いため、ステータスごとに順次 upgrade API を呼ぶ
  // （同一 player_weapon_id への逐次呼び出しのため、後続の呼び出しは先の更新を含んだ状態を返す）
  const handleApplyAll = async () => {
    if (!pilot || !hasPendingUpgrades || !canAffordAll) return;

    setIsApplying(true);
    setMessage(null);

    try {
      let latestPlayerWeapon = playerWeapon;
      let totalCostPaid = 0;
      for (const stat of STAT_TYPES) {
        const steps = getSteps(stat.key);
        if (steps === 0) continue;
        const response = await upgradePlayerWeapon(playerWeapon.id, {
          target_stat: stat.key,
          steps,
        });
        latestPlayerWeapon = response.player_weapon;
        totalCostPaid += response.cost_paid;
      }

      setMessage(`✓ 改造完了！ (合計コスト: ${totalCostPaid.toLocaleString()} Credits)`);
      setPendingSteps({});
      onUpgraded(latestPlayerWeapon);
    } catch (error) {
      setMessage(`✗ エラー: ${error instanceof Error ? error.message : "改造に失敗しました"}`);
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <SciFiModal isOpen onClose={onClose} variant="primary" maxWidthClass="max-w-lg">
      <div className="relative p-4 sm:p-6">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 z-10 text-gray-400 hover:text-[#00ff41] transition-colors font-mono text-sm"
          aria-label="閉じる"
        >
          ✕ CLOSE
        </button>

        <SciFiHeading level={3} className="text-lg sm:text-xl mb-1 pr-20">
          武器改造
        </SciFiHeading>
        <p className="text-sm text-[#00ff41]/70 mb-4">
          {spec.name}
          {spec.type && <span className="ml-2 text-xs text-[#00ff41]/50">{spec.type}</span>}
        </p>

        <div className="space-y-4">
          {/* 所持金（現在 ➔ 変更後） */}
          {pilot && (
            <div className="p-3 bg-[#0a0a0a] rounded border border-[#ffb000]/30 text-sm">
              <span className="text-[#ffb000]">Credits: </span>
              <span className="text-[#ffb000] font-bold">
                {pilot.credits.toLocaleString()}
              </span>
              {hasPendingUpgrades && (
                <>
                  <span className="text-[#ffb000]/60"> ➔ </span>
                  <span
                    className={`font-bold ${
                      canAffordAll ? "text-[#00f0ff]" : "text-red-400"
                    }`}
                  >
                    {(pilot.credits - totalPendingCost).toLocaleString()}
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

          {/* 改造パネル */}
          <div className="divide-y divide-[#00ff41]/10">
            {STAT_TYPES.map((stat) => {
              const steps = getSteps(stat.key);
              const base = stat.getBase(playerWeapon);
              const currentBonus = stat.getBonus(playerWeapon);
              const cap = bonusCap(stat, base);
              const isMaxed = currentBonus >= cap;
              const maxAffordable = pilot
                ? calcMaxAffordableSteps(stat, base, currentBonus, pilot.credits)
                : 0;

              const { totalCost: stepsCost, finalBonus } = simulateSteps(
                stat,
                base,
                currentBonus,
                steps
              );

              const currentRank = getWeaponRank(stat.rankStatName, base + currentBonus);
              const previewRank =
                steps > 0 ? getWeaponRank(stat.rankStatName, base + finalBonus) : null;
              const isRankUp = !!previewRank && previewRank !== currentRank;

              // 現在の1回分のコスト（[-]/[+]横に表示）
              const nextStepCost = isMaxed
                ? 0
                : calcStepCost(stat, currentBonus + steps * stat.increment);

              return (
                <div key={stat.key} className="py-4 first:pt-0">
                  {/* ラベル行 */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-[#00ff41] uppercase tracking-wider">
                      {stat.label}
                    </span>
                    <span
                      className={`text-xs text-[#ffb000] ${steps > 0 ? "visible" : "invisible"}`}
                    >
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
                      currentValue={currentBonus}
                      cap={cap}
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
                        <span className="text-xs text-[#00ff41]/40 font-mono ml-1 w-16 text-right">
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
              loadingLabel="改造中..."
            />
          </div>
        </div>
      </div>
    </SciFiModal>
  );
}
