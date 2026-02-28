"use client";

import { useState, useEffect } from "react";
import { MobileSuit, Pilot, UpgradePreview } from "@/types/battle";
import { upgradeMobileSuit, getUpgradePreview } from "@/services/api";
import { SciFiButton, SciFiPanel } from "@/components/ui";
import { getRankColor } from "@/utils/rankUtils";

type StatType = "hp" | "armor" | "mobility" | "weapon_power" | "melee_aptitude" | "shooting_aptitude" | "accuracy_bonus" | "evasion_bonus" | "acceleration_bonus" | "turning_bonus";

interface StatInfo {
  label: string;
  key: StatType;
  getValue: (ms: MobileSuit) => number;
  format: (val: number) => string;
  /** ランク変換する場合のランクキー名 (hp_rank, armor_rank, mobility_rank) */
  rankKey?: keyof Pick<MobileSuit, "hp_rank" | "armor_rank" | "mobility_rank">;
}

const STAT_TYPES: StatInfo[] = [
  {
    label: "HP",
    key: "hp",
    getValue: (ms) => ms.max_hp,
    format: (val) => val.toFixed(0),
    rankKey: "hp_rank",
  },
  {
    label: "装甲",
    key: "armor",
    getValue: (ms) => ms.armor,
    format: (val) => val.toFixed(0),
    rankKey: "armor_rank",
  },
  {
    label: "機動性",
    key: "mobility",
    getValue: (ms) => ms.mobility,
    format: (val) => val.toFixed(2),
    rankKey: "mobility_rank",
  },
  {
    label: "武器威力",
    key: "weapon_power",
    getValue: (ms) => {
      const weapon = ms.weapons && ms.weapons.length > 0 ? ms.weapons[0] : null;
      return weapon ? weapon.power : 0;
    },
    format: (val) => val.toFixed(0),
  },
  {
    label: "格闘適性",
    key: "melee_aptitude",
    getValue: (ms) => ms.melee_aptitude ?? 1.0,
    format: (val) => `×${val.toFixed(2)}`,
  },
  {
    label: "射撃適性",
    key: "shooting_aptitude",
    getValue: (ms) => ms.shooting_aptitude ?? 1.0,
    format: (val) => `×${val.toFixed(2)}`,
  },
  {
    label: "命中補正",
    key: "accuracy_bonus",
    getValue: (ms) => ms.accuracy_bonus ?? 0.0,
    format: (val) => `${val >= 0 ? "+" : ""}${val.toFixed(1)}%`,
  },
  {
    label: "回避補正",
    key: "evasion_bonus",
    getValue: (ms) => ms.evasion_bonus ?? 0.0,
    format: (val) => `${val >= 0 ? "+" : ""}${val.toFixed(1)}%`,
  },
  {
    label: "加速補正",
    key: "acceleration_bonus",
    getValue: (ms) => ms.acceleration_bonus ?? 0.0,
    format: (val) => `${val >= 0 ? "+" : ""}${val.toFixed(2)}`,
  },
  {
    label: "旋回補正",
    key: "turning_bonus",
    getValue: (ms) => ms.turning_bonus ?? 0.0,
    format: (val) => `${val >= 0 ? "+" : ""}${val.toFixed(2)}`,
  },
];

interface StatusTabProps {
  mobileSuit: MobileSuit;
  pilot: Pilot | undefined;
  onUpgraded: (updatedMs: MobileSuit) => void;
}

export default function StatusTab({ mobileSuit, pilot, onUpgraded }: StatusTabProps) {
  const [previews, setPreviews] = useState<Record<string, UpgradePreview>>({});
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchPreviews = async () => {
      const newPreviews: Record<string, UpgradePreview> = {};
      for (const stat of STAT_TYPES) {
        try {
          const preview = await getUpgradePreview(mobileSuit.id, stat.key);
          newPreviews[stat.key] = preview;
        } catch (error) {
          console.error(`Failed to get preview for ${stat.key}:`, error);
        }
      }
      setPreviews(newPreviews);
    };

    fetchPreviews();
  }, [mobileSuit.id, mobileSuit.max_hp, mobileSuit.armor, mobileSuit.mobility,
      mobileSuit.melee_aptitude, mobileSuit.shooting_aptitude, mobileSuit.accuracy_bonus,
      mobileSuit.evasion_bonus, mobileSuit.acceleration_bonus, mobileSuit.turning_bonus]);

  const handleUpgrade = async (statType: StatType) => {
    if (!pilot) return;

    setUpgrading(statType);
    setMessage(null);

    try {
      const response = await upgradeMobileSuit({
        mobile_suit_id: mobileSuit.id,
        target_stat: statType,
      });

      setMessage(`✓ ${response.message} (コスト: ${response.cost_paid} Credits)`);
      onUpgraded(response.mobile_suit);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      setMessage(`✗ エラー: ${errorMessage}`);
    } finally {
      setUpgrading(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* 基本スペック表示（ランク表記） */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 bg-[#0a0a0a] rounded border border-[#00ff41]/30">
          <div className="text-xs text-[#00ff41]/60">HP</div>
          <div className={`text-lg font-bold ${getRankColor(mobileSuit.hp_rank ?? "C")}`}>
            {mobileSuit.hp_rank ?? "C"}
          </div>
        </div>
        <div className="p-3 bg-[#0a0a0a] rounded border border-[#00ff41]/30">
          <div className="text-xs text-[#00ff41]/60">装甲</div>
          <div className={`text-lg font-bold ${getRankColor(mobileSuit.armor_rank ?? "C")}`}>
            {mobileSuit.armor_rank ?? "C"}
          </div>
        </div>
        <div className="p-3 bg-[#0a0a0a] rounded border border-[#00ff41]/30">
          <div className="text-xs text-[#00ff41]/60">機動性</div>
          <div className={`text-lg font-bold ${getRankColor(mobileSuit.mobility_rank ?? "C")}`}>
            {mobileSuit.mobility_rank ?? "C"}
          </div>
        </div>
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
          <span className="text-[#ffb000] font-bold">{pilot.credits.toLocaleString()} Credits</span>
        </div>
      )}

      {/* メッセージ */}
      {message && (
        <div className={`p-3 rounded border text-sm ${
          message.startsWith("✓")
            ? "bg-[#00ff41]/10 border-[#00ff41]/50 text-[#00ff41]"
            : "bg-red-900/30 border-red-600/50 text-red-300"
        }`}>
          {message}
        </div>
      )}

      {/* 強化パネル */}
      <div className="space-y-3">
        <h4 className="text-sm font-bold text-[#00f0ff] uppercase tracking-wider">
          ステータス強化 (Engineering)
        </h4>
        {STAT_TYPES.map((stat) => {
          const preview = previews[stat.key];
          const currentValue = stat.getValue(mobileSuit);
          const canAfford = pilot && preview ? pilot.credits >= preview.cost : false;
          const isMaxed = preview?.at_max_cap || false;

          // ランク表示用（rankKeyが定義されているステータスのみ）
          const currentRank = stat.rankKey ? mobileSuit[stat.rankKey] : undefined;

          return (
            <div
              key={stat.key}
              className="p-4 bg-[#0a0a0a] rounded border border-[#00ff41]/20"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h5 className="text-sm font-bold mb-1 text-[#00ff41]">{stat.label}</h5>
                  <div className="flex items-center gap-3 text-sm">
                    {currentRank ? (
                      /* ランク変換対象ステータス：ランク表示 */
                      <span>
                        現在: <span className={`font-bold ${getRankColor(currentRank)}`}>{currentRank}</span>
                      </span>
                    ) : (
                      <span>
                        現在: <span className="text-[#ffb000] font-bold">{stat.format(currentValue)}</span>
                      </span>
                    )}
                    {preview && !isMaxed && (
                      <>
                        <span className="text-[#00ff41]/30">→</span>
                        {/* 強化後の値表示（ランク対象は値のみ、ランク変動はバックエンドから更新後に反映） */}
                        <span>
                          強化後: <span className="text-[#00ff41] font-bold">{stat.format(preview.new_value)}</span>
                        </span>
                      </>
                    )}
                  </div>
                  {preview && (
                    <div className="text-xs mt-1">
                      <span className="text-[#00ff41]/60">コスト: </span>
                      <span className={canAfford ? "text-[#00ff41]" : "text-red-400"}>
                        {preview.cost.toLocaleString()} Credits
                      </span>
                    </div>
                  )}
                </div>

                <div>
                  {isMaxed ? (
                    <SciFiButton variant="secondary" size="sm" disabled>
                      最大値
                    </SciFiButton>
                  ) : (
                    <SciFiButton
                      variant="primary"
                      size="sm"
                      onClick={() => handleUpgrade(stat.key)}
                      disabled={!canAfford || upgrading === stat.key || !preview}
                    >
                      {upgrading === stat.key ? "強化中..." : "強化する"}
                    </SciFiButton>
                  )}
                </div>
              </div>
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
                {(mobileSuit.accuracy_bonus ?? 0.0) >= 0 ? "+" : ""}{(mobileSuit.accuracy_bonus ?? 0.0).toFixed(1)}%
              </span>
            </div>
            <div>
              <span className="text-[#00ff41]/60">回避補正:</span>
              <span className="ml-2 font-bold text-[#ffb000]">
                {(mobileSuit.evasion_bonus ?? 0.0) >= 0 ? "+" : ""}{(mobileSuit.evasion_bonus ?? 0.0).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      </SciFiPanel>
    </div>
  );
}

