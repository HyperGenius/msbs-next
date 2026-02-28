/* frontend/src/app/garage/components/MobileSuitList.tsx */
"use client";

import { MobileSuit } from "@/types/battle";
import { SciFiCard, SciFiHeading, SciFiPanel } from "@/components/ui";
import { getRankColor } from "@/utils/rankUtils";

interface MobileSuitListProps {
  mobileSuits: MobileSuit[] | undefined;
  selectedMs: MobileSuit | null;
  onSelect: (ms: MobileSuit) => void;
}

export default function MobileSuitList({
  mobileSuits,
  selectedMs,
  onSelect,
}: MobileSuitListProps) {
  return (
    <SciFiPanel variant="primary">
      <div className="p-4 sm:p-6">
        <SciFiHeading level={3} className="mb-4 text-lg sm:text-xl">
          機体一覧
        </SciFiHeading>

        {mobileSuits && mobileSuits.length > 0 ? (
          <ul className="space-y-2">
            {mobileSuits.map((ms) => {
              const hpRank = ms.hp_rank ?? "?";
              const armorRank = ms.armor_rank ?? "?";
              const mobilityRank = ms.mobility_rank ?? "?";
              return (
                <SciFiCard
                  key={ms.id}
                  variant="primary"
                  interactive
                  onClick={() => onSelect(ms)}
                  className={`p-3 sm:p-4 touch-manipulation ${
                    selectedMs?.id === ms.id ? "bg-[#00ff41]/10" : ""
                  }`}
                >
                  <div className="font-bold text-base sm:text-lg">{ms.name}</div>
                  <div className="text-xs sm:text-sm text-[#00ff41]/70 mt-1 flex gap-3">
                    <span>
                      HP: <span className={`font-bold ${getRankColor(hpRank)}`}>{hpRank}</span>
                    </span>
                    <span>
                      装甲: <span className={`font-bold ${getRankColor(armorRank)}`}>{armorRank}</span>
                    </span>
                    <span>
                      機動性: <span className={`font-bold ${getRankColor(mobilityRank)}`}>{mobilityRank}</span>
                    </span>
                  </div>
                  <div className="text-[10px] sm:text-xs text-[#00ff41]/60 mt-1">
                    対ビーム: {((ms.beam_resistance || 0) * 100).toFixed(0)}% /
                    対実弾: {((ms.physical_resistance || 0) * 100).toFixed(0)}%
                  </div>
                  {ms.weapons && ms.weapons.length > 0 && (
                    <div className="text-[10px] sm:text-xs text-[#00ff41]/60 mt-1">
                      武器: {ms.weapons[0].name} ({ms.weapons[0].type || "PHYSICAL"})
                    </div>
                  )}
                </SciFiCard>
              );
            })}
          </ul>
        ) : (
          <p className="text-[#00ff41]/50 text-sm">機体データがありません。</p>
        )}
      </div>
    </SciFiPanel>
  );
}
