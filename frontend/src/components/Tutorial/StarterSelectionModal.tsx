"use client";

import { useState } from "react";
import { SciFiPanel, SciFiButton, SciFiHeading, SciFiCard } from "@/components/ui";

interface StarterUnit {
  id: "zaku_ii" | "gm";
  name: string;
  type: string;
  description: string;
  specs: {
    hp: number;
    armor: number;
    mobility: number;
    weaponType: string;
    specialFeature: string;
  };
}

const STARTER_UNITS: StarterUnit[] = [
  {
    id: "zaku_ii",
    name: "Zaku II",
    type: "攻撃重視型",
    description: "ジオン軍の主力量産機。実弾兵器を主体とした攻撃的な運用が可能。",
    specs: {
      hp: 800,
      armor: 50,
      mobility: 1.0,
      weaponType: "実弾 (Zaku Machine Gun)",
      specialFeature: "物理耐性 20%",
    },
  },
  {
    id: "gm",
    name: "RGM-79 GM",
    type: "バランス型",
    description: "連邦軍の量産機。ビーム兵器を装備し、防御とのバランスに優れる。",
    specs: {
      hp: 750,
      armor: 45,
      mobility: 1.1,
      weaponType: "ビーム (Beam Spray Gun)",
      specialFeature: "ビーム耐性 10%",
    },
  },
];

interface StarterSelectionModalProps {
  onSelect: (unitId: "zaku_ii" | "gm") => void;
  isLoading: boolean;
}

export default function StarterSelectionModal({
  onSelect,
  isLoading,
}: StarterSelectionModalProps) {
  const [selectedUnit, setSelectedUnit] = useState<"zaku_ii" | "gm" | null>(null);

  const handleConfirm = () => {
    if (selectedUnit) {
      onSelect(selectedUnit);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm animate-fade-in">
      <div className="max-w-5xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <SciFiPanel variant="accent" className="p-6 md:p-8">
          {/* ヘッダー */}
          <div className="mb-6 text-center">
            <SciFiHeading level={1} variant="accent" className="text-3xl md:text-4xl mb-3">
              初期機体選択
            </SciFiHeading>
            <p className="text-sm md:text-base text-[#00f0ff]/80">
              あなたの最初の機体を選択してください。戦闘スタイルに合わせた選択が可能です。
            </p>
          </div>

          {/* 機体選択グリッド */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 mb-6">
            {STARTER_UNITS.map((unit) => (
              <button
                key={unit.id}
                onClick={() => setSelectedUnit(unit.id)}
                disabled={isLoading}
                className={`text-left transition-all ${
                  selectedUnit === unit.id
                    ? "scale-105"
                    : "hover:scale-[1.02]"
                }`}
              >
                <SciFiCard
                  variant={selectedUnit === unit.id ? "accent" : "secondary"}
                  interactive={true}
                  className={
                    selectedUnit === unit.id
                      ? "sf-border-glow-cyan"
                      : "hover:sf-border-glow-cyan/50"
                  }
                >
                  <div className="space-y-4">
                    {/* 機体名とタイプ */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-2xl font-bold text-[#00f0ff]">
                          {unit.name}
                        </h3>
                        {selectedUnit === unit.id && (
                          <div className="w-8 h-8 bg-[#00f0ff] rounded-full flex items-center justify-center animate-pulse">
                            <span className="text-black font-bold">✓</span>
                          </div>
                        )}
                      </div>
                      <div className="inline-block px-3 py-1 bg-[#00f0ff]/20 border border-[#00f0ff]/50 text-[#00f0ff] text-sm font-bold">
                        {unit.type}
                      </div>
                    </div>

                    {/* 説明文 */}
                    <p className="text-sm text-[#00f0ff]/70 leading-relaxed">
                      {unit.description}
                    </p>

                    {/* スペック表示 */}
                    <div className="space-y-2">
                      <p className="text-xs text-[#00f0ff]/60 font-bold uppercase tracking-wider">
                        Specifications
                      </p>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="bg-[#0a0a0a]/70 p-2 border border-[#00f0ff]/30">
                          <p className="text-[#00f0ff]/60 text-xs mb-1">HP</p>
                          <p className="text-[#00f0ff] font-bold">{unit.specs.hp}</p>
                        </div>
                        <div className="bg-[#0a0a0a]/70 p-2 border border-[#00f0ff]/30">
                          <p className="text-[#00f0ff]/60 text-xs mb-1">装甲</p>
                          <p className="text-[#00f0ff] font-bold">{unit.specs.armor}</p>
                        </div>
                        <div className="bg-[#0a0a0a]/70 p-2 border border-[#00f0ff]/30">
                          <p className="text-[#00f0ff]/60 text-xs mb-1">機動性</p>
                          <p className="text-[#00f0ff] font-bold">{unit.specs.mobility}</p>
                        </div>
                        <div className="bg-[#0a0a0a]/70 p-2 border border-[#00f0ff]/30">
                          <p className="text-[#00f0ff]/60 text-xs mb-1">武器</p>
                          <p className="text-[#00f0ff] font-bold text-xs">
                            {unit.specs.weaponType}
                          </p>
                        </div>
                      </div>
                      
                      {/* 特殊能力 */}
                      <div className="bg-[#00f0ff]/10 p-3 border border-[#00f0ff]/40">
                        <p className="text-xs text-[#00f0ff]/60 mb-1">特殊能力</p>
                        <p className="text-[#00f0ff] font-bold text-sm">
                          {unit.specs.specialFeature}
                        </p>
                      </div>
                    </div>
                  </div>
                </SciFiCard>
              </button>
            ))}
          </div>

          {/* 決定ボタン */}
          <SciFiButton
            onClick={handleConfirm}
            disabled={!selectedUnit || isLoading}
            variant="accent"
            size="lg"
            className="w-full"
          >
            {isLoading ? "機体配備中..." : selectedUnit ? "この機体で開始" : "機体を選択してください"}
          </SciFiButton>

          {/* 注意事項 */}
          <p className="text-xs text-center text-[#00f0ff]/50 mt-4">
            ※ 初期機体はゲーム開始時に配備されます。後から他の機体も入手可能です。
          </p>
        </SciFiPanel>
      </div>
    </div>
  );
}
