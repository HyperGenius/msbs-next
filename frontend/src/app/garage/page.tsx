/* frontend/src/app/garage/page.tsx */
"use client";

import { useState } from "react";
import { useMobileSuits, updateMobileSuit, usePilot, useWeaponListings, equipWeapon } from "@/services/api";
import { MobileSuit, Weapon } from "@/types/battle";
import Link from "next/link";
import Header from "@/components/Header";
import { SciFiPanel, SciFiButton, SciFiHeading, SciFiInput, SciFiCard, SciFiSelect } from "@/components/ui";

// 武器スロット定義
const WEAPON_SLOTS = [
  { index: 0, label: "Main Weapon", labelJa: "メイン武器" },
  { index: 1, label: "Sub Weapon", labelJa: "サブ武器" },
] as const;

// 武器パラメータの差分を計算する
function calcWeaponDiff(current: Weapon | undefined, candidate: Weapon): {
  power: number;
  range: number;
  accuracy: number;
} {
  return {
    power: candidate.power - (current?.power ?? 0),
    range: candidate.range - (current?.range ?? 0),
    accuracy: candidate.accuracy - (current?.accuracy ?? 0),
  };
}

// 差分値の色クラスを返す
function diffColor(val: number): string {
  if (val > 0) return "text-green-400";
  if (val < 0) return "text-red-400";
  return "text-gray-400";
}

// 差分値の表示文字列を返す
function diffText(val: number): string {
  if (val > 0) return `+${val}`;
  if (val < 0) return `${val}`;
  return "±0";
}

export default function GaragePage() {
  const { mobileSuits, isLoading, isError, mutate } = useMobileSuits();
  const { pilot } = usePilot();
  const { weaponListings } = useWeaponListings();
  const [selectedMs, setSelectedMs] = useState<MobileSuit | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showWeaponModal, setShowWeaponModal] = useState(false);
  const [selectedWeaponSlot, setSelectedWeaponSlot] = useState(0);
  // プレビュー中の武器 (武器変更モーダル内でホバー/フォーカスした武器)
  const [previewWeaponId, setPreviewWeaponId] = useState<string | null>(null);

  // フォーム用のstate
  const [formData, setFormData] = useState({
    name: "",
    max_hp: 0,
    armor: 0,
    mobility: 0,
    tactics: {
      priority: "CLOSEST" as "CLOSEST" | "WEAKEST" | "RANDOM" | "STRONGEST" | "THREAT",
      range: "BALANCED" as "MELEE" | "RANGED" | "BALANCED" | "FLEE",
    },
  });

  // 機体選択時の処理
  const handleSelectMs = (ms: MobileSuit) => {
    setSelectedMs(ms);
    setFormData({
      name: ms.name,
      max_hp: ms.max_hp,
      armor: ms.armor,
      mobility: ms.mobility,
      tactics: ms.tactics || {
        priority: "CLOSEST",
        range: "BALANCED",
      },
    });
    setSuccessMessage(null);
  };

  // フォーム送信処理
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMs) return;

    setIsSaving(true);
    setSuccessMessage(null);

    try {
      const updatedData = await updateMobileSuit(selectedMs.id, formData);
      setSuccessMessage("機体データを更新しました");
      
      // SWRのキャッシュを更新
      mutate();
      
      // 選択中の機体情報も更新（API responseを使用）
      setSelectedMs(updatedData);
    } catch (error) {
      console.error("Update error:", error);
      alert("更新に失敗しました。");
    } finally {
      setIsSaving(false);
    }
  };

  // 武器変更モーダルを開く
  const handleOpenWeaponModal = (slotIndex: number) => {
    setSelectedWeaponSlot(slotIndex);
    setPreviewWeaponId(null);
    setShowWeaponModal(true);
  };

  // 武器を装備
  const handleEquipWeapon = async (weaponId: string) => {
    if (!selectedMs) return;

    setIsSaving(true);
    try {
      const updatedMs = await equipWeapon(selectedMs.id, {
        weapon_id: weaponId,
        slot_index: selectedWeaponSlot,
      });
      
      setSuccessMessage("武器を装備しました");
      setShowWeaponModal(false);
      setPreviewWeaponId(null);
      
      // SWRのキャッシュを更新
      mutate();
      
      // 選択中の機体情報も更新
      setSelectedMs(updatedMs);
    } catch (error) {
      console.error("Equip error:", error);
      alert(error instanceof Error ? error.message : "武器の装備に失敗しました");
    } finally {
      setIsSaving(false);
    }
  };

  if (isError) {
    return (
      <div className="min-h-screen bg-[#050505] text-[#00ff41] p-8 font-mono">
        <div className="max-w-6xl mx-auto">
          <SciFiPanel variant="secondary">
            <div className="p-6">
              <p className="text-[#ffb000] font-bold text-xl mb-2">ERROR: データ取得失敗</p>
              <p className="text-sm">Backendが起動しているか確認してください。</p>
            </div>
          </SciFiPanel>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[#050505] text-[#00ff41] p-4 sm:p-6 md:p-8 font-mono">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <Header />
        <div className="mb-4 sm:mb-8 border-b-2 border-[#00ff41]/30 pb-4">
          <div className="flex flex-col sm:flex-row gap-4 sm:gap-0 justify-between items-start sm:items-center">
            <div>
              <SciFiHeading level={2} className="text-xl sm:text-2xl">GARAGE - Mobile Suit Hangar</SciFiHeading>
              <p className="text-xs sm:text-sm text-[#00ff41]/60 ml-0 sm:ml-5">機体管理システム</p>
            </div>
            <Link href="/" className="w-full sm:w-auto">
              <SciFiButton variant="primary" size="sm" className="w-full sm:w-auto">&lt; Back to Simulator</SciFiButton>
            </Link>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <SciFiPanel variant="accent">
              <div className="p-8">
                <p className="text-xl animate-pulse text-[#00f0ff]">LOADING DATA...</p>
              </div>
            </SciFiPanel>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            {/* Left Pane: 機体リスト */}
            <SciFiPanel variant="primary">
              <div className="p-4 sm:p-6">
                <SciFiHeading level={3} className="mb-4 text-lg sm:text-xl">機体一覧</SciFiHeading>
              
                {mobileSuits && mobileSuits.length > 0 ? (
                  <ul className="space-y-2">
                    {mobileSuits.map((ms) => (
                      <SciFiCard
                        key={ms.id}
                        variant="primary"
                        interactive
                        onClick={() => handleSelectMs(ms)}
                        className={`p-3 sm:p-4 touch-manipulation ${
                          selectedMs?.id === ms.id
                            ? "bg-[#00ff41]/10"
                            : ""
                        }`}
                      >
                        <div className="font-bold text-base sm:text-lg">{ms.name}</div>
                        <div className="text-xs sm:text-sm text-[#00ff41]/70 mt-1">
                          HP: {ms.max_hp} / 装甲: {ms.armor} / 機動性: {ms.mobility}
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
                    ))}
                  </ul>
                ) : (
                  <p className="text-[#00ff41]/50 text-sm">機体データがありません。</p>
                )}
              </div>
            </SciFiPanel>

            {/* Right Pane: ステータス編集フォーム */}
            <SciFiPanel variant="accent">
              <div className="p-4 sm:p-6">
                <SciFiHeading level={3} className="mb-4 text-lg sm:text-xl" variant="accent">
                  機体ステータス編集
                </SciFiHeading>

              {selectedMs ? (
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* 名前 */}
                  <SciFiInput
                    label="機体名"
                    type="text"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    variant="accent"
                  />

                  {/* Max HP */}
                  <SciFiInput
                    label="最大HP"
                    type="number"
                    value={formData.max_hp}
                    onChange={(e) =>
                      setFormData({ ...formData, max_hp: Number(e.target.value) })
                    }
                    variant="accent"
                  />

                  {/* Armor */}
                  <SciFiInput
                    label="装甲"
                    type="number"
                    value={formData.armor}
                    onChange={(e) =>
                      setFormData({ ...formData, armor: Number(e.target.value) })
                    }
                    variant="accent"
                  />

                  {/* Mobility */}
                  <SciFiInput
                    label="機動性"
                    type="number"
                    step="0.1"
                    value={formData.mobility}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        mobility: Number(e.target.value),
                      })
                    }
                    variant="accent"
                  />

                  {/* Specs Display Section */}
                  <div className="pt-4 border-t border-green-800">
                    <h3 className="text-lg font-bold mb-4 text-green-300">
                      機体スペック (詳細)
                    </h3>
                    
                    {/* Energy & Propellant Display */}
                    <div className="mb-4 p-3 bg-gray-900 rounded">
                      <h4 className="text-sm font-bold mb-2 text-cyan-400">
                        エネルギー・推進剤
                      </h4>
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <span className="text-gray-400">最大EN:</span>
                          <span className="ml-2 font-bold text-cyan-400">
                            {selectedMs.max_en || 1000}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400">EN回復:</span>
                          <span className="ml-2 font-bold text-cyan-400">
                            {selectedMs.en_recovery || 100}/ターン
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400">最大推進剤:</span>
                          <span className="ml-2 font-bold text-purple-400">
                            {selectedMs.max_propellant || 1000}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Resistance Display */}
                    <div className="mb-4 p-3 bg-gray-900 rounded">
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <span className="text-gray-400">対ビーム防御:</span>
                          <span className="ml-2 font-bold text-blue-400">
                            {((selectedMs.beam_resistance || 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400">対実弾防御:</span>
                          <span className="ml-2 font-bold text-yellow-400">
                            {((selectedMs.physical_resistance || 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Terrain Adaptability Display */}
                    <div className="mb-4 p-3 bg-gray-900 rounded border border-green-800">
                      <h4 className="text-sm font-bold mb-2 text-green-400">
                        地形適正
                      </h4>
                      <div className="grid grid-cols-4 gap-2 text-xs">
                        {[
                          { env: "SPACE", label: "宇宙", icon: "🌌" },
                          { env: "GROUND", label: "地上", icon: "🏔️" },
                          { env: "COLONY", label: "コロニー", icon: "🏢" },
                          { env: "UNDERWATER", label: "水中", icon: "🌊" }
                        ].map(({ env, label, icon }) => {
                          const rank = selectedMs.terrain_adaptability?.[env] || "A";
                          const getRankColor = (r: string) => {
                            switch (r) {
                              case "S": return "text-green-400";
                              case "A": return "text-blue-400";
                              case "B": return "text-yellow-400";
                              case "C": return "text-orange-400";
                              case "D": return "text-red-400";
                              default: return "text-gray-400";
                            }
                          };
                          const getRankModifier = (r: string) => {
                            switch (r) {
                              case "S": return "+20%";
                              case "A": return "±0%";
                              case "B": return "-20%";
                              case "C": return "-40%";
                              case "D": return "-60%";
                              default: return "±0%";
                            }
                          };
                          return (
                            <div key={env} className="p-2 bg-gray-800 rounded text-center">
                              <div className="text-base mb-1">{icon}</div>
                              <div className="text-xs text-gray-400 mb-1">{label}</div>
                              <div className={`text-lg font-bold ${getRankColor(rank)}`}>
                                {rank}
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                {getRankModifier(rank)}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                      <p className="text-xs text-green-600 mt-2 opacity-70">
                        地形適正により移動速度が変化します
                      </p>
                    </div>

                    {/* Loadout: Main / Sub Weapon Slots */}
                    <div className="p-3 bg-gray-900 rounded border border-green-800">
                      <h4 className="text-sm font-bold mb-3 text-green-500">
                        装備換装 (Loadout)
                      </h4>
                      <div className="space-y-3">
                        {WEAPON_SLOTS.map((slot) => {
                          const equippedWeapon = selectedMs.weapons?.[slot.index];
                          return (
                            <div key={slot.index} className="p-2 bg-gray-800 rounded">
                              <div className="flex justify-between items-center mb-2">
                                <div>
                                  <span className="text-xs font-bold text-green-400 uppercase">
                                    [{slot.index === 0 ? "MAIN" : "SUB"}]
                                  </span>
                                  <span className="ml-2 text-xs text-gray-400">
                                    {slot.labelJa}
                                  </span>
                                </div>
                                <SciFiButton
                                  variant="primary"
                                  size="sm"
                                  onClick={() => handleOpenWeaponModal(slot.index)}
                                >
                                  変更
                                </SciFiButton>
                              </div>
                              {equippedWeapon ? (
                                <div className="text-xs space-y-1">
                                  <div className="font-bold text-green-300">
                                    {equippedWeapon.name}
                                  </div>
                                  <div className="grid grid-cols-3 gap-2">
                                    <div>
                                      <span className={`px-1 py-0.5 text-xs font-bold rounded ${
                                        equippedWeapon.type === "BEAM"
                                          ? "bg-blue-500/20 text-blue-400"
                                          : "bg-yellow-500/20 text-yellow-400"
                                      }`}>
                                        {equippedWeapon.type || "PHYSICAL"}
                                      </span>
                                    </div>
                                    <div>
                                      <span className="text-gray-400">威力:</span>
                                      <span className="ml-1 font-bold">{equippedWeapon.power}</span>
                                    </div>
                                    <div>
                                      <span className="text-gray-400">射程:</span>
                                      <span className="ml-1 font-bold">{equippedWeapon.range}m</span>
                                    </div>
                                    <div>
                                      <span className="text-gray-400">命中:</span>
                                      <span className="ml-1 font-bold">{equippedWeapon.accuracy}%</span>
                                    </div>
                                    <div>
                                      <span className="text-gray-400">最適:</span>
                                      <span className="ml-1 font-bold text-green-400">
                                        {equippedWeapon.optimal_range || 300}m
                                      </span>
                                    </div>
                                    <div>
                                      <span className="text-gray-400">弾数:</span>
                                      <span className="ml-1 font-bold text-orange-400">
                                        {equippedWeapon.max_ammo != null
                                          ? equippedWeapon.max_ammo
                                          : "∞"}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <div className="text-xs text-gray-500 py-2 text-center">
                                  — 未装備 —
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Tactics Section */}
                  <div className="pt-4 border-t border-green-800">
                    <h3 className="text-lg font-bold mb-4 text-green-300">
                      戦術設定 (Tactics)
                    </h3>
                    
                    {/* Target Priority */}
                    <div className="mb-4">
                      <SciFiSelect
                        label="ターゲット優先度"
                        helpText="攻撃対象の選択方法を設定します"
                        variant="accent"
                        value={formData.tactics.priority}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            tactics: {
                              ...formData.tactics,
                              priority: e.target.value as "CLOSEST" | "WEAKEST" | "RANDOM" | "STRONGEST" | "THREAT",
                            },
                          })
                        }
                        options={[
                          { value: "CLOSEST", label: "CLOSEST - 最寄りの敵" },
                          { value: "WEAKEST", label: "WEAKEST - HP最小の敵" },
                          { value: "STRONGEST", label: "STRONGEST - 強敵優先 (戦略価値)" },
                          { value: "THREAT", label: "THREAT - 脅威度優先" },
                          { value: "RANDOM", label: "RANDOM - ランダム選択" },
                        ]}
                      />
                    </div>

                    {/* Engagement Range */}
                    <div>
                      <SciFiSelect
                        label="交戦距離設定"
                        helpText="戦闘時の移動パターンを設定します"
                        variant="accent"
                        value={formData.tactics.range}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            tactics: {
                              ...formData.tactics,
                              range: e.target.value as "MELEE" | "RANGED" | "BALANCED" | "FLEE",
                            },
                          })
                        }
                        options={[
                          { value: "MELEE", label: "MELEE - 近接突撃" },
                          { value: "RANGED", label: "RANGED - 遠距離維持" },
                          { value: "BALANCED", label: "BALANCED - バランス型" },
                          { value: "FLEE", label: "FLEE - 回避優先" },
                        ]}
                      />
                    </div>
                  </div>

                  {/* Success Message */}
                  {successMessage && (
                    <SciFiPanel variant="primary" chiseled={false}>
                      <div className="p-3 text-[#00ff41] animate-pulse">
                        {successMessage}
                      </div>
                    </SciFiPanel>
                  )}

                  {/* Submit Button */}
                  <SciFiButton
                    type="submit"
                    disabled={isSaving}
                    variant="accent"
                    size="lg"
                    className="w-full"
                  >
                    {isSaving ? "保存中..." : "保存"}
                  </SciFiButton>
                </form>
              ) : (
                <div className="flex items-center justify-center h-64 text-[#00ff41]/30">
                  <p>機体を選択してください</p>
                </div>
              )}
              </div>
            </SciFiPanel>
          </div>
        )}

        {/* Weapon Change Modal */}
        {showWeaponModal && selectedMs && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
            <SciFiPanel variant="accent" chiseled={true}>
              <div className="p-8 max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
                <SciFiHeading level={3} className="mb-1" variant="accent">
                  武器変更
                </SciFiHeading>
                <p className="mb-1 text-xs text-green-600">
                  スロット: {selectedWeaponSlot === 0 ? "【MAIN】メイン武器" : "【SUB】サブ武器"}
                </p>
                <p className="mb-4 text-sm text-green-400">
                  所持している武器から選択してください
                </p>

                {/* Current weapon for diff comparison */}
                {(() => {
                  const currentWeapon = selectedMs.weapons?.[selectedWeaponSlot];
                  const previewListing = previewWeaponId
                    ? weaponListings?.find((w) => w.id === previewWeaponId)
                    : null;

                  return previewListing ? (
                    <div className="mb-4 p-3 bg-gray-900 rounded border border-green-700">
                      <p className="text-xs font-bold text-green-400 mb-2">
                        ▶ 装備変更プレビュー: {previewListing.weapon.name}
                      </p>
                      {(() => {
                        const diff = calcWeaponDiff(currentWeapon, previewListing.weapon);
                        return (
                          <div className="grid grid-cols-3 gap-2 text-xs">
                            <div>
                              <span className="text-gray-400">威力:</span>
                              <span className="ml-1 font-bold">{previewListing.weapon.power}</span>
                              <span className={`ml-1 ${diffColor(diff.power)}`}>
                                ({diffText(diff.power)})
                              </span>
                            </div>
                            <div>
                              <span className="text-gray-400">射程:</span>
                              <span className="ml-1 font-bold">{previewListing.weapon.range}m</span>
                              <span className={`ml-1 ${diffColor(diff.range)}`}>
                                ({diffText(diff.range)})
                              </span>
                            </div>
                            <div>
                              <span className="text-gray-400">命中:</span>
                              <span className="ml-1 font-bold">{previewListing.weapon.accuracy}%</span>
                              <span className={`ml-1 ${diffColor(diff.accuracy)}`}>
                                ({diffText(diff.accuracy)})
                              </span>
                            </div>
                          </div>
                        );
                      })()}
                    </div>
                  ) : null;
                })()}

                {/* Available Weapons List */}
                <div className="space-y-3 mb-6">
                  {weaponListings
                    ?.filter(
                      (weaponListing) =>
                        pilot?.inventory &&
                        pilot.inventory[weaponListing.id] &&
                        pilot.inventory[weaponListing.id] > 0
                    )
                    .map((weaponListing) => {
                      const weapon = weaponListing.weapon;
                      const currentWeapon = selectedMs.weapons?.[selectedWeaponSlot];
                      const diff = calcWeaponDiff(currentWeapon, weapon);
                      return (
                        <div
                          key={weaponListing.id}
                          onMouseEnter={() => setPreviewWeaponId(weaponListing.id)}
                          onMouseLeave={() => setPreviewWeaponId(null)}
                        >
                        <SciFiCard
                          variant="accent"
                          className="cursor-pointer hover:border-green-400 transition-colors"
                          onClick={() => handleEquipWeapon(weaponListing.id)}
                        >
                          <div className="p-4">
                            <div className="flex justify-between items-start mb-2">
                              <div>
                                <h4 className="font-bold text-green-300">
                                  {weapon.name}
                                </h4>
                                <p className="text-xs text-green-600">
                                  所持数: {pilot?.inventory?.[weaponListing.id] || 0}
                                </p>
                              </div>
                              <span className={`px-2 py-1 text-xs font-bold rounded ${
                                weapon.type === "BEAM" 
                                  ? "bg-blue-500/20 text-blue-400" 
                                  : "bg-yellow-500/20 text-yellow-400"
                              }`}>
                                {weapon.type || "PHYSICAL"}
                              </span>
                            </div>
                            
                            <div className="grid grid-cols-3 gap-2 text-xs">
                              <div>
                                <span className="text-gray-400">威力:</span>
                                <span className="ml-1 font-bold text-green-400">
                                  {weapon.power}
                                </span>
                                {currentWeapon && (
                                  <span className={`ml-1 text-xs ${diffColor(diff.power)}`}>
                                    ({diffText(diff.power)})
                                  </span>
                                )}
                              </div>
                              <div>
                                <span className="text-gray-400">射程:</span>
                                <span className="ml-1 font-bold text-green-400">
                                  {weapon.range}m
                                </span>
                                {currentWeapon && (
                                  <span className={`ml-1 text-xs ${diffColor(diff.range)}`}>
                                    ({diffText(diff.range)})
                                  </span>
                                )}
                              </div>
                              <div>
                                <span className="text-gray-400">命中:</span>
                                <span className="ml-1 font-bold text-green-400">
                                  {weapon.accuracy}%
                                </span>
                                {currentWeapon && (
                                  <span className={`ml-1 text-xs ${diffColor(diff.accuracy)}`}>
                                    ({diffText(diff.accuracy)})
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </SciFiCard>
                        </div>
                      );
                    })}
                  
                  {(!pilot?.inventory ||
                    !weaponListings?.some(
                      (w) =>
                        pilot.inventory?.[w.id] &&
                        pilot.inventory[w.id] > 0
                    )) && (
                    <div className="text-center py-8 text-gray-400">
                      <p>所持している武器がありません</p>
                      <p className="text-sm mt-2">
                        ショップで武器を購入してください
                      </p>
                    </div>
                  )}
                </div>

                <div className="flex gap-4">
                  <SciFiButton
                    onClick={() => {
                      setShowWeaponModal(false);
                      setPreviewWeaponId(null);
                    }}
                    variant="danger"
                    size="md"
                    className="flex-1"
                  >
                    閉じる
                  </SciFiButton>
                </div>
              </div>
            </SciFiPanel>
          </div>
        )}
      </div>
    </main>
  );
}

