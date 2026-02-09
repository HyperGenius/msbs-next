/* frontend/src/app/garage/page.tsx */
"use client";

import { useState } from "react";
import { useMobileSuits, updateMobileSuit } from "@/services/api";
import { MobileSuit } from "@/types/battle";
import Link from "next/link";
import Header from "@/components/Header";

export default function GaragePage() {
  const { mobileSuits, isLoading, isError, mutate } = useMobileSuits();
  const [selectedMs, setSelectedMs] = useState<MobileSuit | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

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

  if (isError) {
    return (
      <div className="min-h-screen bg-gray-900 text-green-400 p-8 font-mono">
        <div className="max-w-6xl mx-auto">
          <p className="text-red-500">データの取得に失敗しました。</p>
          <p className="text-sm mt-2">Backendが起動しているか確認してください。</p>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gray-900 text-green-400 p-8 font-mono">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <Header />
        <div className="mb-8 border-b border-green-700 pb-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold">GARAGE - Mobile Suit Hangar</h2>
              <p className="text-sm opacity-70">機体管理システム</p>
            </div>
            <Link
              href="/"
              className="px-4 py-2 bg-green-900 hover:bg-green-800 rounded font-bold transition-colors"
            >
              &lt; Back to Simulator
            </Link>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <p className="text-xl animate-pulse">LOADING DATA...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left Pane: 機体リスト */}
            <div className="bg-gray-800 p-6 rounded-lg border border-green-800">
              <h2 className="text-xl font-bold mb-4 border-l-4 border-green-500 pl-2">
                機体一覧
              </h2>
              
              {mobileSuits && mobileSuits.length > 0 ? (
                <ul className="space-y-2">
                  {mobileSuits.map((ms) => (
                    <li
                      key={ms.id}
                      onClick={() => handleSelectMs(ms)}
                      className={`p-4 rounded border cursor-pointer transition-colors ${
                        selectedMs?.id === ms.id
                          ? "bg-green-900 border-green-500"
                          : "bg-gray-900 border-green-800 hover:border-green-600"
                      }`}
                    >
                      <div className="font-bold text-lg">{ms.name}</div>
                      <div className="text-sm opacity-70 mt-1">
                        HP: {ms.max_hp} / 装甲: {ms.armor} / 機動性: {ms.mobility}
                      </div>
                      <div className="text-xs opacity-60 mt-1">
                        対ビーム: {((ms.beam_resistance || 0) * 100).toFixed(0)}% / 
                        対実弾: {((ms.physical_resistance || 0) * 100).toFixed(0)}%
                      </div>
                      {ms.weapons && ms.weapons.length > 0 && (
                        <div className="text-xs opacity-60 mt-1">
                          武器: {ms.weapons[0].name} ({ms.weapons[0].type || "PHYSICAL"})
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="opacity-50">機体データがありません。</p>
              )}
            </div>

            {/* Right Pane: ステータス編集フォーム */}
            <div className="bg-gray-800 p-6 rounded-lg border border-green-800">
              <h2 className="text-xl font-bold mb-4 border-l-4 border-green-500 pl-2">
                機体ステータス編集
              </h2>

              {selectedMs ? (
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* 名前 */}
                  <div>
                    <label className="block text-sm font-bold mb-2">機体名</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                      className="w-full px-3 py-2 bg-gray-900 border border-green-700 rounded focus:border-green-500 focus:outline-none"
                    />
                  </div>

                  {/* Max HP */}
                  <div>
                    <label className="block text-sm font-bold mb-2">最大HP</label>
                    <input
                      type="number"
                      value={formData.max_hp}
                      onChange={(e) =>
                        setFormData({ ...formData, max_hp: Number(e.target.value) })
                      }
                      className="w-full px-3 py-2 bg-gray-900 border border-green-700 rounded focus:border-green-500 focus:outline-none"
                    />
                  </div>

                  {/* Armor */}
                  <div>
                    <label className="block text-sm font-bold mb-2">装甲</label>
                    <input
                      type="number"
                      value={formData.armor}
                      onChange={(e) =>
                        setFormData({ ...formData, armor: Number(e.target.value) })
                      }
                      className="w-full px-3 py-2 bg-gray-900 border border-green-700 rounded focus:border-green-500 focus:outline-none"
                    />
                  </div>

                  {/* Mobility */}
                  <div>
                    <label className="block text-sm font-bold mb-2">機動性</label>
                    <input
                      type="number"
                      step="0.1"
                      value={formData.mobility}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          mobility: Number(e.target.value),
                        })
                      }
                      className="w-full px-3 py-2 bg-gray-900 border border-green-700 rounded focus:border-green-500 focus:outline-none"
                    />
                  </div>

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

                    {/* Weapons Display */}
                    {selectedMs.weapons && selectedMs.weapons.length > 0 && (
                      <div className="p-3 bg-gray-900 rounded">
                        <h4 className="text-sm font-bold mb-2 text-green-500">
                          装備武器
                        </h4>
                        {selectedMs.weapons.map((weapon, idx) => (
                          <div key={idx} className="mb-3 text-sm border-b border-green-800 pb-2 last:border-b-0">
                            <div className="font-bold">{weapon.name}</div>
                            <div className="grid grid-cols-2 gap-2 text-xs mt-1">
                              <div>
                                <span className="text-gray-400">属性:</span>
                                <span className={`ml-2 font-bold ${
                                  weapon.type === "BEAM" ? "text-blue-400" : "text-yellow-400"
                                }`}>
                                  {weapon.type || "PHYSICAL"}
                                </span>
                              </div>
                              <div>
                                <span className="text-gray-400">威力:</span>
                                <span className="ml-2 font-bold">{weapon.power}</span>
                              </div>
                              <div>
                                <span className="text-gray-400">射程:</span>
                                <span className="ml-2 font-bold">{weapon.range}m</span>
                              </div>
                              <div>
                                <span className="text-gray-400">最適射程:</span>
                                <span className="ml-2 font-bold text-green-400">
                                  {weapon.optimal_range || 300}m
                                </span>
                              </div>
                              <div>
                                <span className="text-gray-400">命中率:</span>
                                <span className="ml-2 font-bold">{weapon.accuracy}%</span>
                              </div>
                              <div>
                                <span className="text-gray-400">減衰率:</span>
                                <span className="ml-2 font-bold">
                                  {((weapon.decay_rate || 0.05) * 100).toFixed(1)}%/100m
                                </span>
                              </div>
                              {/* Resource Info */}
                              <div>
                                <span className="text-gray-400">弾数:</span>
                                <span className="ml-2 font-bold text-orange-400">
                                  {weapon.max_ammo !== null && weapon.max_ammo !== undefined 
                                    ? weapon.max_ammo 
                                    : "∞"}
                                </span>
                              </div>
                              <div>
                                <span className="text-gray-400">EN消費:</span>
                                <span className="ml-2 font-bold text-cyan-400">
                                  {weapon.en_cost || 0}
                                </span>
                              </div>
                              <div>
                                <span className="text-gray-400">クールタイム:</span>
                                <span className="ml-2 font-bold text-pink-400">
                                  {weapon.cool_down_turn || 0}ターン
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Tactics Section */}
                  <div className="pt-4 border-t border-green-800">
                    <h3 className="text-lg font-bold mb-4 text-green-300">
                      戦術設定 (Tactics)
                    </h3>
                    
                    {/* Target Priority */}
                    <div className="mb-4">
                      <label className="block text-sm font-bold mb-2">
                        ターゲット優先度
                      </label>
                      <select
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
                        className="w-full px-3 py-2 bg-gray-900 border border-green-700 rounded focus:border-green-500 focus:outline-none"
                      >
                        <option value="CLOSEST">CLOSEST - 最寄りの敵</option>
                        <option value="WEAKEST">WEAKEST - HP最小の敵</option>
                        <option value="STRONGEST">STRONGEST - 強敵優先 (戦略価値)</option>
                        <option value="THREAT">THREAT - 脅威度優先</option>
                        <option value="RANDOM">RANDOM - ランダム選択</option>
                      </select>
                      <p className="text-xs text-green-600 mt-1">
                        攻撃対象の選択方法を設定します
                      </p>
                    </div>

                    {/* Engagement Range */}
                    <div>
                      <label className="block text-sm font-bold mb-2">
                        交戦距離設定
                      </label>
                      <select
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
                        className="w-full px-3 py-2 bg-gray-900 border border-green-700 rounded focus:border-green-500 focus:outline-none"
                      >
                        <option value="MELEE">MELEE - 近接突撃</option>
                        <option value="RANGED">RANGED - 遠距離維持</option>
                        <option value="BALANCED">BALANCED - バランス型</option>
                        <option value="FLEE">FLEE - 回避優先</option>
                      </select>
                      <p className="text-xs text-green-600 mt-1">
                        戦闘時の移動パターンを設定します
                      </p>
                    </div>
                  </div>

                  {/* Success Message */}
                  {successMessage && (
                    <div className="p-3 bg-green-900/50 border border-green-500 rounded text-green-300 animate-pulse">
                      {successMessage}
                    </div>
                  )}

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={isSaving}
                    className={`w-full px-4 py-3 rounded font-bold text-black transition-colors ${
                      isSaving
                        ? "bg-gray-500 cursor-not-allowed"
                        : "bg-green-500 hover:bg-green-400"
                    }`}
                  >
                    {isSaving ? "保存中..." : "保存"}
                  </button>
                </form>
              ) : (
                <div className="flex items-center justify-center h-64 opacity-30">
                  <p>機体を選択してください</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
