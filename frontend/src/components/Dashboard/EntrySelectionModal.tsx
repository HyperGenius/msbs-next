"use client";

import { MobileSuit } from "@/types/battle";
import { SciFiPanel, SciFiButton, SciFiHeading, SciFiCard } from "@/components/ui";

interface EntrySelectionModalProps {
  mobileSuits: MobileSuit[];
  onSelect: (mobileSuitId: string) => void;
  onCancel: () => void;
  isLoading: boolean;
}

export default function EntrySelectionModal({
  mobileSuits,
  onSelect,
  onCancel,
  isLoading,
}: EntrySelectionModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <SciFiPanel variant="primary" className="p-6">
          <div className="mb-6">
            <SciFiHeading level={2} variant="primary" className="text-2xl mb-2">
              出撃機体選択
            </SciFiHeading>
            <p className="text-sm text-[#00ff41]/60">
              バトルに出撃させる機体を選択してください
            </p>
          </div>

          {/* 機体リスト */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {mobileSuits.map((ms) => (
              <SciFiCard
                key={ms.id}
                variant="primary"
                interactive={true}
                className="hover:sf-border-glow-green"
              >
                <div className="space-y-3">
                  {/* 機体名 */}
                  <div className="flex items-center justify-between">
                    <h3 className="text-xl font-bold text-[#00ff41]">
                      {ms.name}
                    </h3>
                    <div className="w-12 h-12 bg-[#00ff41]/20 rounded border-2 border-[#00ff41]/50 flex items-center justify-center">
                      <span className="text-2xl">🤖</span>
                    </div>
                  </div>

                  {/* ステータス表示 */}
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="bg-[#0a0a0a]/70 p-2 border border-[#00ff41]/30">
                      <p className="text-[#00ff41]/60 text-xs mb-1">HP</p>
                      <p className="text-[#00ff41] font-bold">{ms.max_hp}</p>
                    </div>
                    <div className="bg-[#0a0a0a]/70 p-2 border border-[#00ff41]/30">
                      <p className="text-[#00ff41]/60 text-xs mb-1">装甲</p>
                      <p className="text-[#00ff41] font-bold">{ms.armor}</p>
                    </div>
                    <div className="bg-[#0a0a0a]/70 p-2 border border-[#00ff41]/30">
                      <p className="text-[#00ff41]/60 text-xs mb-1">機動性</p>
                      <p className="text-[#00ff41] font-bold">{ms.mobility}</p>
                    </div>
                    <div className="bg-[#0a0a0a]/70 p-2 border border-[#00ff41]/30">
                      <p className="text-[#00ff41]/60 text-xs mb-1">武器</p>
                      <p className="text-[#00ff41] font-bold">{ms.weapons.length}基</p>
                    </div>
                  </div>

                  {/* 武器リスト */}
                  <div className="border-t border-[#00ff41]/20 pt-2">
                    <p className="text-xs text-[#00ff41]/60 mb-1">装備武器:</p>
                    <div className="space-y-1">
                      {ms.weapons.map((weapon, idx) => (
                        <div
                          key={`${ms.id}-weapon-${idx}`}
                          className="text-xs text-[#00ff41]/80 flex items-center justify-between"
                        >
                          <span>• {weapon.name}</span>
                          <span className="text-[#00ff41]/50">威力: {weapon.power}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 選択ボタン */}
                  <SciFiButton
                    onClick={() => onSelect(ms.id)}
                    disabled={isLoading}
                    variant="primary"
                    className="w-full"
                  >
                    {isLoading ? "エントリー中..." : "この機体で出撃"}
                  </SciFiButton>
                </div>
              </SciFiCard>
            ))}
          </div>

          {/* キャンセルボタン */}
          <SciFiButton
            onClick={onCancel}
            disabled={isLoading}
            variant="secondary"
            className="w-full"
          >
            キャンセル
          </SciFiButton>
        </SciFiPanel>
      </div>
    </div>
  );
}
