"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { SignedIn, SignedOut } from "@clerk/nextjs";
import { useMobileSuits, usePilot, upgradeMobileSuit, getUpgradePreview } from "@/services/api";
import Header from "@/components/Header";
import type { MobileSuit, UpgradePreview } from "@/types/battle";

type StatType = "hp" | "armor" | "mobility" | "weapon_power";

interface StatInfo {
  label: string;
  key: StatType;
  getValue: (ms: MobileSuit) => number;
  format: (val: number) => string;
}

const STAT_TYPES: StatInfo[] = [
  {
    label: "HP",
    key: "hp",
    getValue: (ms) => ms.max_hp,
    format: (val) => val.toFixed(0),
  },
  {
    label: "装甲",
    key: "armor",
    getValue: (ms) => ms.armor,
    format: (val) => val.toFixed(0),
  },
  {
    label: "機動性",
    key: "mobility",
    getValue: (ms) => ms.mobility,
    format: (val) => val.toFixed(2),
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
];

export default function EngineeringPage() {
  const router = useRouter();
  const { mobileSuits, isLoading: suitsLoading, mutate: mutateSuits } = useMobileSuits();
  const { pilot, mutate: mutatePilot } = usePilot();
  
  const [selectedMobileSuit, setSelectedMobileSuit] = useState<MobileSuit | null>(null);
  const [previews, setPreviews] = useState<Record<string, UpgradePreview>>({});
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // 所有している機体のみをフィルタ
  const ownedMobileSuits = mobileSuits?.filter((ms) => ms.user_id) || [];

  // 機体を選択したときにプレビューを取得
  useEffect(() => {
    if (!selectedMobileSuit) {
      setPreviews({});
      return;
    }

    const fetchPreviews = async () => {
      const newPreviews: Record<string, UpgradePreview> = {};
      for (const stat of STAT_TYPES) {
        try {
          const preview = await getUpgradePreview(selectedMobileSuit.id, stat.key);
          newPreviews[stat.key] = preview;
        } catch (error) {
          console.error(`Failed to get preview for ${stat.key}:`, error);
        }
      }
      setPreviews(newPreviews);
    };

    fetchPreviews();
  }, [selectedMobileSuit]);

  const handleUpgrade = async (statType: StatType) => {
    if (!selectedMobileSuit || !pilot) return;

    setUpgrading(statType);
    setMessage(null);

    try {
      const response = await upgradeMobileSuit({
        mobile_suit_id: selectedMobileSuit.id,
        target_stat: statType,
      });

      setMessage(`✓ ${response.message} (コスト: ${response.cost_paid} Credits)`);
      
      // データを再取得
      await mutateSuits();
      await mutatePilot();
      
      // 選択中の機体を更新
      setSelectedMobileSuit(response.mobile_suit);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      setMessage(`✗ エラー: ${errorMessage}`);
    } finally {
      setUpgrading(null);
    }
  };

  return (
    <div className="min-h-screen bg-black text-green-400 p-8 font-mono">
      <Header />

      <SignedOut>
        <div className="text-center py-20">
          <p className="text-xl mb-4">機体改造にはログインが必要です</p>
          <button
            onClick={() => router.push("/")}
            className="px-6 py-3 bg-green-900 hover:bg-green-800 rounded"
          >
            ホームに戻る
          </button>
        </div>
      </SignedOut>

      <SignedIn>
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-bold mb-2 text-green-300">Engineering Factory</h2>
          <p className="text-lg mb-8 opacity-70">機体改造 - ステータス強化</p>

          {/* 所持金表示 */}
          {pilot && (
            <div className="mb-6 p-4 bg-gray-900 rounded border border-green-700">
              <div className="text-xl">
                <span className="text-gray-400">所持金: </span>
                <span className="text-green-400 font-bold">{pilot.credits.toLocaleString()} Credits</span>
              </div>
            </div>
          )}

          {/* メッセージ表示 */}
          {message && (
            <div className={`mb-6 p-4 rounded border ${
              message.startsWith("✓") 
                ? "bg-green-900/30 border-green-600 text-green-300" 
                : "bg-red-900/30 border-red-600 text-red-300"
            }`}>
              {message}
            </div>
          )}

          {/* 機体選択 */}
          <div className="mb-8">
            <h3 className="text-2xl font-bold mb-4">機体選択</h3>
            
            {suitsLoading ? (
              <p>読み込み中...</p>
            ) : ownedMobileSuits.length === 0 ? (
              <div className="p-6 bg-gray-900 rounded border border-yellow-600">
                <p className="text-yellow-400">所有している機体がありません。</p>
                <button
                  onClick={() => router.push("/shop")}
                  className="mt-4 px-6 py-2 bg-blue-900 hover:bg-blue-800 rounded"
                >
                  ショップへ
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {ownedMobileSuits.map((ms) => (
                  <button
                    key={ms.id}
                    onClick={() => setSelectedMobileSuit(ms)}
                    className={`p-4 rounded border-2 transition-all text-left ${
                      selectedMobileSuit?.id === ms.id
                        ? "border-green-500 bg-green-900/30"
                        : "border-gray-700 bg-gray-900 hover:border-green-700"
                    }`}
                  >
                    <h4 className="text-xl font-bold mb-2">{ms.name}</h4>
                    <div className="text-sm space-y-1">
                      <div>HP: {ms.max_hp}</div>
                      <div>装甲: {ms.armor}</div>
                      <div>機動性: {ms.mobility.toFixed(2)}</div>
                      {ms.weapons && ms.weapons.length > 0 && (
                        <div>武器: {ms.weapons[0].name} ({ms.weapons[0].power})</div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 強化画面 */}
          {selectedMobileSuit && (
            <div className="mt-8">
              <h3 className="text-2xl font-bold mb-4">{selectedMobileSuit.name} - ステータス強化</h3>
              
              <div className="space-y-4">
                {STAT_TYPES.map((stat) => {
                  const preview = previews[stat.key];
                  const currentValue = stat.getValue(selectedMobileSuit);
                  const canAfford = pilot && preview ? pilot.credits >= preview.cost : false;
                  const isMaxed = preview?.at_max_cap || false;

                  return (
                    <div
                      key={stat.key}
                      className="p-6 bg-gray-900 rounded border border-gray-700"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <h4 className="text-xl font-bold mb-2">{stat.label}</h4>
                          <div className="flex items-center gap-4 mb-2">
                            <span className="text-lg">
                              現在: <span className="text-yellow-400 font-bold">{stat.format(currentValue)}</span>
                            </span>
                            {preview && !isMaxed && (
                              <>
                                <span className="text-gray-500">→</span>
                                <span className="text-lg">
                                  強化後: <span className="text-green-400 font-bold">{stat.format(preview.new_value)}</span>
                                </span>
                              </>
                            )}
                          </div>
                          {preview && (
                            <div className="text-sm">
                              <span className="text-gray-400">コスト: </span>
                              <span className={canAfford ? "text-green-400" : "text-red-400"}>
                                {preview.cost.toLocaleString()} Credits
                              </span>
                            </div>
                          )}
                        </div>
                        
                        <div>
                          {isMaxed ? (
                            <div className="px-6 py-3 bg-gray-700 text-gray-400 rounded cursor-not-allowed">
                              最大値
                            </div>
                          ) : (
                            <button
                              onClick={() => handleUpgrade(stat.key)}
                              disabled={!canAfford || upgrading === stat.key || !preview}
                              className={`px-6 py-3 rounded font-bold transition-all ${
                                upgrading === stat.key
                                  ? "bg-yellow-700 text-yellow-200 cursor-wait"
                                  : canAfford
                                  ? "bg-green-700 hover:bg-green-600 text-white shadow-lg hover:shadow-green-500/50"
                                  : "bg-gray-700 text-gray-400 cursor-not-allowed"
                              }`}
                            >
                              {upgrading === stat.key ? "強化中..." : "強化する"}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </SignedIn>
    </div>
  );
}
