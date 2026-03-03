/* frontend/src/app/garage/components/MobileSuitList.tsx */
"use client";

import { EnrichedMobileSuit } from "@/utils/rankUtils";
import { SciFiCard, SciFiHeading, SciFiPanel } from "@/components/ui";

interface MobileSuitListProps {
  mobileSuits: EnrichedMobileSuit[] | undefined;
  selectedMs: EnrichedMobileSuit | null;
  onSelect: (ms: EnrichedMobileSuit) => void;
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
          MS一覧
        </SciFiHeading>

        {mobileSuits && mobileSuits.length > 0 ? (
          <ul className="space-y-2">
            {mobileSuits.map((ms) => {
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
                      HP: <span className={`font-bold ${ms.display.hp.colorClass}`}>{ms.display.hp.rank}</span>
                    </span>
                    <span>
                      装甲: <span className={`font-bold ${ms.display.armor.colorClass}`}>{ms.display.armor.rank}</span>
                    </span>
                    <span>
                      機動性: <span className={`font-bold ${ms.display.mobility.colorClass}`}>{ms.display.mobility.rank}</span>
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
