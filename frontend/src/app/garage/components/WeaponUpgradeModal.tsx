/* frontend/src/app/garage/components/WeaponUpgradeModal.tsx */
"use client";

import { useCallback, useEffect, useState } from "react";
import { PlayerWeapon, Pilot, WeaponUpgradeStatType, WeaponUpgradePreview } from "@/types/battle";
import { getWeaponUpgradePreview, upgradePlayerWeapon } from "@/services/api";
import SciFiModal from "@/components/ui/SciFiModal";
import { SciFiCard, SciFiHeading } from "@/components/ui";
import HoldSciFiButton from "@/components/ui/HoldSciFiButton";
import { getRankColor, getWeaponRank } from "@/utils/rankUtils";

interface WeaponUpgradeModalProps {
  playerWeapon: PlayerWeapon;
  pilot: Pilot | undefined;
  onClose: () => void;
  /** 改造成功時に呼ばれる（更新後の PlayerWeapon を渡す） */
  onUpgraded: (updated: PlayerWeapon) => void;
}

const STAT_LABELS: Record<WeaponUpgradeStatType, string> = {
  power_bonus: "威力",
  accuracy_bonus: "命中率",
};

const STAT_RANK_NAME: Record<WeaponUpgradeStatType, "weapon_power" | "weapon_accuracy"> = {
  power_bonus: "weapon_power",
  accuracy_bonus: "weapon_accuracy",
};

/** base_snapshot + custom_stats から現在の実効値（power/accuracy）を取り出す */
function getEffectiveValue(playerWeapon: PlayerWeapon, statType: WeaponUpgradeStatType): number {
  const base = playerWeapon.base_snapshot as { power?: number; accuracy?: number };
  const baseValue = statType === "power_bonus" ? (base.power ?? 0) : (base.accuracy ?? 0);
  const bonus = playerWeapon.custom_stats?.[statType] ?? 0;
  return baseValue + bonus;
}

export default function WeaponUpgradeModal({
  playerWeapon,
  pilot,
  onClose,
  onUpgraded,
}: WeaponUpgradeModalProps) {
  const [previews, setPreviews] = useState<
    Partial<Record<WeaponUpgradeStatType, WeaponUpgradePreview>>
  >({});
  const [isLoadingPreview, setIsLoadingPreview] = useState(true);
  const [applyingStat, setApplyingStat] = useState<WeaponUpgradeStatType | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const spec = playerWeapon.base_snapshot as { name?: string; type?: string };

  const loadPreviews = useCallback(async () => {
    setIsLoadingPreview(true);
    try {
      const [powerPreview, accuracyPreview] = await Promise.all([
        getWeaponUpgradePreview(playerWeapon.id, "power_bonus"),
        getWeaponUpgradePreview(playerWeapon.id, "accuracy_bonus"),
      ]);
      setPreviews({ power_bonus: powerPreview, accuracy_bonus: accuracyPreview });
    } catch (error) {
      setMessage(
        `✗ エラー: ${error instanceof Error ? error.message : "プレビューの取得に失敗しました"}`
      );
    } finally {
      setIsLoadingPreview(false);
    }
  }, [playerWeapon.id]);

  useEffect(() => {
    loadPreviews();
  }, [loadPreviews]);

  const handleUpgrade = async (statType: WeaponUpgradeStatType) => {
    setApplyingStat(statType);
    setMessage(null);
    try {
      const response = await upgradePlayerWeapon(playerWeapon.id, {
        target_stat: statType,
        steps: 1,
      });
      setMessage(
        `✓ ${STAT_LABELS[statType]}を改造しました！ (コスト: ${response.cost_paid.toLocaleString()} Credits)`
      );
      onUpgraded(response.player_weapon);
      await loadPreviews();
    } catch (error) {
      setMessage(`✗ エラー: ${error instanceof Error ? error.message : "改造に失敗しました"}`);
    } finally {
      setApplyingStat(null);
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

        {pilot && (
          <div className="p-3 mb-4 bg-[#0a0a0a] rounded border border-[#ffb000]/30 text-sm">
            <span className="text-[#ffb000]">Credits: </span>
            <span className="text-[#ffb000] font-bold">{pilot.credits.toLocaleString()}</span>
          </div>
        )}

        {message && (
          <div
            className={`p-3 mb-4 rounded border text-sm ${
              message.startsWith("✓")
                ? "bg-[#00ff41]/10 border-[#00ff41]/50 text-[#00ff41]"
                : "bg-red-900/30 border-red-600/50 text-red-300"
            }`}
          >
            {message}
          </div>
        )}

        <div className="space-y-3">
          {(Object.keys(STAT_LABELS) as WeaponUpgradeStatType[]).map((statType) => {
            const preview = previews[statType];
            const currentValue = getEffectiveValue(playerWeapon, statType);
            const currentRank = getWeaponRank(STAT_RANK_NAME[statType], currentValue);
            const previewRank = preview
              ? getWeaponRank(STAT_RANK_NAME[statType], preview.new_value)
              : null;
            const isRankUp = !!previewRank && previewRank !== currentRank;
            const isMaxed = preview?.at_max_cap ?? false;
            const canAfford = pilot ? pilot.credits >= (preview?.cost ?? Infinity) : false;
            const isApplying = applyingStat === statType;

            return (
              <SciFiCard key={statType} variant="primary" className="p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-[#00ff41] uppercase tracking-wider">
                    {STAT_LABELS[statType]}
                  </span>
                  <span
                    className={`text-base font-bold font-mono ${getRankColor(
                      isRankUp ? previewRank! : currentRank
                    )}`}
                  >
                    {isRankUp ? previewRank : currentRank}
                    {isRankUp && (
                      <span className="ml-1 text-[#00f0ff] text-xs animate-pulse">✨UP!</span>
                    )}
                  </span>
                </div>

                <div className="flex items-center justify-between text-sm text-[#00ff41]/70 mb-3">
                  <span>
                    {currentValue.toFixed(statType === "power_bonus" ? 0 : 1)}
                    {preview && !isMaxed && (
                      <>
                        {" → "}
                        <span className="text-[#00f0ff] font-bold">
                          {preview.new_value.toFixed(statType === "power_bonus" ? 0 : 1)}
                        </span>
                      </>
                    )}
                  </span>
                  {!isMaxed && preview && (
                    <span className="text-xs text-[#ffb000]">
                      {preview.cost.toLocaleString()} CR
                    </span>
                  )}
                </div>

                {isMaxed ? (
                  <div className="text-center py-2 border border-[#00ff41]/30 text-xs text-[#00ff41]/40 font-bold">
                    上限に達しています
                  </div>
                ) : (
                  <HoldSciFiButton
                    onHoldComplete={() => handleUpgrade(statType)}
                    disabled={isLoadingPreview || !preview || !canAfford}
                    loading={isApplying}
                    label={
                      isLoadingPreview || !preview
                        ? "読み込み中..."
                        : `長押しで改造 (${preview.cost.toLocaleString()} Credits)`
                    }
                    loadingLabel="改造中..."
                  />
                )}
              </SciFiCard>
            );
          })}
        </div>
      </div>
    </SciFiModal>
  );
}
