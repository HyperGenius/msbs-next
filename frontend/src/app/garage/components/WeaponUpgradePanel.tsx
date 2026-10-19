/* frontend/src/app/garage/components/WeaponUpgradePanel.tsx */
"use client";

import { useMemo, useState } from "react";
import { PlayerWeapon, Pilot } from "@/types/battle";
import { upgradePlayerWeapon } from "@/services/api";
import { SciFiBlockIndicator } from "@/components/ui";
import HoldSciFiButton from "@/components/ui/HoldSciFiButton";
import { getRankColor, getWeaponRank } from "@/utils/rankUtils";
import {
  WEAPON_UPGRADE_STATS,
  bonusCap,
  calcMaxAffordableSteps,
  calcStepCost,
  simulateSteps,
} from "../weaponUpgrade";

interface WeaponUpgradePanelProps {
  playerWeapon: PlayerWeapon;
  pilot: Pilot | undefined;
  /** 改造成功時に呼ばれる（更新後の PlayerWeapon を渡す） */
  onUpgraded: (updated: PlayerWeapon) => void;
}

const STEPPER_BUTTON_CLASS =
  "touch-manipulation w-11 h-11 font-mono font-bold text-base border border-[#00ff41]/40 text-[#00ff41] bg-[#050505] hover:bg-[#00ff41]/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors";

/** 武器改造モーダルの「改造」タブ。中身をスクロールさせ、長押し確定ボタンはフッターに固定する。 */
export default function WeaponUpgradePanel({
  playerWeapon,
  pilot,
  onUpgraded,
}: WeaponUpgradePanelProps) {
  const [pendingSteps, setPendingSteps] = useState<Record<string, number>>({});
  const [isApplying, setIsApplying] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const getSteps = (key: string) => pendingSteps[key] ?? 0;
  const setSteps = (key: string, steps: number) =>
    setPendingSteps((prev) => ({ ...prev, [key]: steps }));

  /** 全ステータスの合計確定コスト */
  const totalPendingCost = useMemo(() => {
    return WEAPON_UPGRADE_STATS.reduce((sum, stat) => {
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
      for (const stat of WEAPON_UPGRADE_STATS) {
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
    <>
      <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 space-y-3 sm:space-y-4">
        {/* 所持金（現在 ➔ 変更後） */}
        {pilot && (
          <div className="p-2 sm:p-3 bg-[#0a0a0a] rounded border border-[#ffb000]/30 text-sm">
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

        <div className="divide-y divide-[#00ff41]/10">
          {WEAPON_UPGRADE_STATS.map((stat) => {
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

            // 次の1回分のコスト（[-]/[+]横に表示）。finalBonus は simulateSteps で
            // cap にクランプ済みのため、ペンディング分ですでに上限に達している
            // 場合は素の (currentBonus + steps * increment) を使わずここで弾く
            const nextStepCost =
              isMaxed || finalBonus >= cap ? 0 : calcStepCost(stat, finalBonus);

            return (
              <div key={stat.key} className="py-3 sm:py-4 first:pt-0">
                {/* RANK UP! はラベル行に置く。ランクバッジ横に置くと、スマホ幅で
                    インジケーターとステッパーが 1 行に収まらないため。 */}
                <div className="flex items-center justify-between mb-2">
                  <span className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[#00ff41] uppercase tracking-wider">
                      {stat.label}
                    </span>
                    <span
                      className={`text-[#00f0ff] text-xs font-bold animate-pulse whitespace-nowrap ${
                        isRankUp ? "visible" : "invisible"
                      }`}
                    >
                      ✨RANK UP!
                    </span>
                  </span>
                  <span
                    className={`text-xs text-[#ffb000] ${steps > 0 ? "visible" : "invisible"}`}
                  >
                    Credits: {stepsCost.toLocaleString()} CR
                  </span>
                </div>

                {/* 狭い画面ではステッパーが次の行の右端に折り返す */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className={`shrink-0 text-base font-bold font-mono border px-1.5 py-0.5 ${
                      isRankUp
                        ? `${getRankColor(previewRank!)} border-current`
                        : `${getRankColor(currentRank)} border-current/40`
                    }`}
                  >
                    {isRankUp ? previewRank : currentRank}
                  </span>

                  <SciFiBlockIndicator
                    currentValue={currentBonus}
                    cap={cap}
                    pendingSteps={steps}
                    increment={stat.increment}
                    className="flex-1"
                  />

                  {isMaxed ? (
                    <span className="ml-auto text-xs text-[#00ff41]/40 font-mono">MAX</span>
                  ) : (
                    <div className="ml-auto flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setSteps(stat.key, Math.max(0, steps - 1))}
                        disabled={steps === 0}
                        className={STEPPER_BUTTON_CLASS}
                        aria-label={`${stat.label} ステップを1減らす`}
                      >
                        −
                      </button>
                      <span className="w-6 text-center text-sm font-mono text-[#00ff41]/70">
                        {steps}
                      </span>
                      <button
                        type="button"
                        onClick={() =>
                          setSteps(stat.key, Math.min(maxAffordable, steps + 1))
                        }
                        disabled={steps >= maxAffordable}
                        className={STEPPER_BUTTON_CLASS}
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
      </div>

      <div className="shrink-0 p-4 sm:px-6 border-t border-[#00ff41]/20">
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
    </>
  );
}
