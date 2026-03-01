/* frontend/src/components/Dashboard/RewardPanel.tsx */
import { BattleRewards } from "@/types/battle";
import { SciFiPanel, SciFiHeading } from "@/components/ui";

interface RewardPanelProps {
  rewards: BattleRewards | null;
}

/**
 * バトル報酬（経験値・クレジット・レベルアップ）を表示するパネル。
 */
export default function RewardPanel({ rewards }: RewardPanelProps) {
  if (!rewards) return null;

  return (
    <SciFiPanel variant="secondary" className="mb-4 sm:mb-8">
      <div className="p-4 sm:p-6">
        <SciFiHeading
          level={2}
          variant="secondary"
          className="mb-4 text-xl sm:text-2xl"
        >
          獲得報酬
        </SciFiHeading>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-[#0a0a0a]/70 p-3 sm:p-4 border-2 border-[#00ff41]/30">
            <p className="text-xs sm:text-sm text-[#00ff41]/60 mb-2">経験値</p>
            <p className="text-2xl sm:text-3xl font-bold text-[#00ff41]">
              +{rewards.exp_gained}
            </p>
            <p className="text-xs text-[#00ff41]/50 mt-2">
              累積: {rewards.total_exp} EXP
            </p>
          </div>
          <div className="bg-[#0a0a0a]/70 p-3 sm:p-4 border-2 border-[#ffb000]/30">
            <p className="text-xs sm:text-sm text-[#ffb000]/60 mb-2">
              クレジット
            </p>
            <p className="text-2xl sm:text-3xl font-bold text-[#ffb000]">
              +{rewards.credits_gained.toLocaleString()}
            </p>
            <p className="text-xs text-[#ffb000]/50 mt-2">
              所持金: {rewards.total_credits.toLocaleString()} CR
            </p>
          </div>
        </div>
        {rewards.level_after > rewards.level_before && (
          <div className="mt-4 p-3 sm:p-4 bg-[#ffb000]/20 border-2 border-[#ffb000] animate-pulse">
            <p className="text-center text-lg sm:text-xl font-bold text-[#ffb000]">
              🎉 LEVEL UP! Lv.{rewards.level_before} → Lv.{rewards.level_after}{" "}
              🎉
            </p>
          </div>
        )}
      </div>
    </SciFiPanel>
  );
}
