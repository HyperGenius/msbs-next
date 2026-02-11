/* frontend/src/app/shop/page.tsx */
"use client";

import { useState } from "react";
import { useShopListings, purchaseMobileSuit, usePilot, useWeaponListings, purchaseWeapon } from "@/services/api";
import { ShopListing, WeaponListing } from "@/types/battle";
import Link from "next/link";
import Header from "@/components/Header";
import { SciFiPanel, SciFiButton, SciFiHeading, SciFiCard } from "@/components/ui";

type TabType = "mobile_suits" | "weapons";

export default function ShopPage() {
  const { listings, isLoading, isError } = useShopListings();
  const { weaponListings, isLoading: weaponsLoading, isError: weaponsError } = useWeaponListings();
  const { pilot, mutate: mutatePilot } = usePilot();
  const [activeTab, setActiveTab] = useState<TabType>("mobile_suits");
  const [selectedItem, setSelectedItem] = useState<ShopListing | null>(null);
  const [selectedWeapon, setSelectedWeapon] = useState<WeaponListing | null>(null);
  const [isPurchasing, setIsPurchasing] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [showWeaponDialog, setShowWeaponDialog] = useState(false);
  const [purchaseMessage, setPurchaseMessage] = useState<string | null>(null);

  const handlePurchaseClick = (item: ShopListing) => {
    setSelectedItem(item);
    setShowConfirmDialog(true);
    setPurchaseMessage(null);
  };

  const handleConfirmPurchase = async () => {
    if (!selectedItem) return;

    setIsPurchasing(true);
    setPurchaseMessage(null);

    try {
      const result = await purchaseMobileSuit(selectedItem.id);
      setPurchaseMessage(result.message);
      
      // パイロット情報を更新
      mutatePilot();
      
      // 成功メッセージを表示後、ダイアログを閉じる
      setTimeout(() => {
        setShowConfirmDialog(false);
        setSelectedItem(null);
      }, 2000);
    } catch (error) {
      if (error instanceof Error) {
        setPurchaseMessage(`エラー: ${error.message}`);
      } else {
        setPurchaseMessage("購入に失敗しました");
      }
    } finally {
      setIsPurchasing(false);
    }
  };

  const handleCancelPurchase = () => {
    setShowConfirmDialog(false);
    setSelectedItem(null);
    setPurchaseMessage(null);
  };

  const handleWeaponPurchaseClick = (weapon: WeaponListing) => {
    setSelectedWeapon(weapon);
    setShowWeaponDialog(true);
    setPurchaseMessage(null);
  };

  const handleConfirmWeaponPurchase = async () => {
    if (!selectedWeapon) return;

    setIsPurchasing(true);
    setPurchaseMessage(null);

    try {
      const result = await purchaseWeapon(selectedWeapon.id);
      setPurchaseMessage(result.message);
      
      // パイロット情報を更新
      mutatePilot();
      
      // 成功メッセージを表示後、ダイアログを閉じる
      setTimeout(() => {
        setShowWeaponDialog(false);
        setSelectedWeapon(null);
      }, 2000);
    } catch (error) {
      if (error instanceof Error) {
        setPurchaseMessage(`エラー: ${error.message}`);
      } else {
        setPurchaseMessage("購入に失敗しました");
      }
    } finally {
      setIsPurchasing(false);
    }
  };

  const handleCancelWeaponPurchase = () => {
    setShowWeaponDialog(false);
    setSelectedWeapon(null);
    setPurchaseMessage(null);
  };

  const canAfford = (price: number): boolean => {
    return pilot ? pilot.credits >= price : false;
  };

  if (isError || weaponsError) {
    return (
      <div className="min-h-screen bg-[#050505] text-[#00ff41] p-8 font-mono">
        <div className="max-w-7xl mx-auto">
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
    <main className="min-h-screen bg-[#050505] text-[#00ff41] p-8 font-mono">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <Header />

        {/* Page Title */}
        <div className="mb-8 border-b-2 border-[#ffb000]/30 pb-4">
          <div className="flex justify-between items-center">
            <div>
              <SciFiHeading level={2} variant="secondary">SHOP</SciFiHeading>
              <p className="text-sm text-[#ffb000]/60 ml-5">ショップ</p>
            </div>
            <Link href="/garage">
              <SciFiButton variant="primary" size="sm">&lt; Back to Garage</SciFiButton>
            </Link>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="mb-6 flex gap-4">
          <SciFiButton
            variant={activeTab === "mobile_suits" ? "secondary" : "primary"}
            onClick={() => setActiveTab("mobile_suits")}
            size="md"
          >
            モビルスーツ (Mobile Suits)
          </SciFiButton>
          <SciFiButton
            variant={activeTab === "weapons" ? "secondary" : "primary"}
            onClick={() => setActiveTab("weapons")}
            size="md"
          >
            武器 (Weapons)
          </SciFiButton>
        </div>

        {(isLoading || weaponsLoading) ? (
          <div className="flex justify-center items-center h-64">
            <SciFiPanel variant="secondary">
              <div className="p-8">
                <p className="text-xl animate-pulse text-[#ffb000]">LOADING INVENTORY...</p>
              </div>
            </SciFiPanel>
          </div>
        ) : (
          <>
            {/* Mobile Suits Tab */}
            {activeTab === "mobile_suits" && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {listings?.map((item) => {
                const affordable = canAfford(item.price);
                
                return (
                  <SciFiCard
                    key={item.id}
                    variant={affordable ? "secondary" : "primary"}
                    className={affordable ? "" : "opacity-60"}
                  >
                    {/* Item Header */}
                    <div className="mb-4">
                      <h3 className="text-xl font-bold text-[#ffb000] mb-2">
                        {item.name}
                      </h3>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-2xl font-bold text-[#ffb000]">
                          {item.price.toLocaleString()} C
                        </span>
                        {!affordable && (
                          <span className="text-sm text-red-400 font-bold">
                            所持金不足
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-[#00ff41]/60">{item.description}</p>
                    </div>

                    {/* Specs */}
                    <div className="mb-4 p-3 bg-[#0a0a0a] border-2 border-[#ffb000]/30">
                      <h4 className="text-sm font-bold mb-2 text-[#ffb000]">
                        SPECIFICATIONS
                      </h4>
                      <div className="grid grid-cols-2 gap-2 text-sm mb-3 text-[#00ff41]">
                        <div>
                          <span className="text-[#00ff41]/60">HP:</span>
                          <span className="ml-2 font-bold">{item.specs.max_hp}</span>
                        </div>
                        <div>
                          <span className="text-[#00ff41]/60">装甲:</span>
                          <span className="ml-2 font-bold">{item.specs.armor}</span>
                        </div>
                        <div>
                          <span className="text-[#00ff41]/60">機動性:</span>
                          <span className="ml-2 font-bold">{item.specs.mobility}</span>
                        </div>
                        <div>
                          <span className="text-[#00ff41]/60">武器:</span>
                          <span className="ml-2 font-bold">
                            {item.specs.weapons[0]?.name || "N/A"}
                          </span>
                        </div>
                      </div>
                      
                      {/* Resistance Info */}
                      <div className="border-t-2 border-[#ffb000]/30 pt-2 mb-2">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span className="text-[#00ff41]/60">対ビーム:</span>
                            <span className="ml-2 font-bold text-[#00f0ff]">
                              {((item.specs.beam_resistance || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">対実弾:</span>
                            <span className="ml-2 font-bold text-[#ffb000]">
                              {((item.specs.physical_resistance || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Weapon Details */}
                      {item.specs.weapons && item.specs.weapons.length > 0 && (
                        <div className="border-t-2 border-[#ffb000]/30 pt-2">
                          <div className="text-xs">
                            <div className="font-bold text-[#00ff41] mb-1">
                              {item.specs.weapons[0].name}
                            </div>
                            <div className="grid grid-cols-2 gap-1">
                              <div>
                                <span className="text-[#00ff41]/60">属性:</span>
                                <span className={`ml-1 font-bold ${
                                  item.specs.weapons[0].type === "BEAM" 
                                    ? "text-[#00f0ff]" 
                                    : "text-[#ffb000]"
                                }`}>
                                  {item.specs.weapons[0].type || "PHYSICAL"}
                                </span>
                              </div>
                              <div>
                                <span className="text-[#00ff41]/60">威力:</span>
                                <span className="ml-1 font-bold">
                                  {item.specs.weapons[0].power}
                                </span>
                              </div>
                              <div>
                                <span className="text-[#00ff41]/60">最適射程:</span>
                                <span className="ml-1 font-bold text-[#00ff41]">
                                  {item.specs.weapons[0].optimal_range || 300}m
                                </span>
                              </div>
                              <div>
                                <span className="text-[#00ff41]/60">命中:</span>
                                <span className="ml-1 font-bold">
                                  {item.specs.weapons[0].accuracy}%
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Purchase Button */}
                    <SciFiButton
                      onClick={() => handlePurchaseClick(item)}
                      disabled={!affordable || isPurchasing}
                      variant={affordable ? "secondary" : "danger"}
                      size="md"
                      className="w-full"
                    >
                      {affordable ? "購入する (BUY)" : "購入不可"}
                    </SciFiButton>
                  </SciFiCard>
                );
              })}
            </div>
            )}

            {/* Weapons Tab */}
            {activeTab === "weapons" && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {weaponListings?.map((weapon) => {
                  const affordable = canAfford(weapon.price);
                  
                  return (
                    <SciFiCard
                      key={weapon.id}
                      variant={affordable ? "secondary" : "primary"}
                      className={affordable ? "" : "opacity-60"}
                    >
                      {/* Weapon Header */}
                      <div className="mb-4">
                        <h3 className="text-xl font-bold text-[#ffb000] mb-2">
                          {weapon.name}
                        </h3>
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-2xl font-bold text-[#ffb000]">
                            {weapon.price.toLocaleString()} C
                          </span>
                          {!affordable && (
                            <span className="text-sm text-red-400 font-bold">
                              所持金不足
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-[#00ff41]/60">{weapon.description}</p>
                      </div>

                      {/* Weapon Specs */}
                      <div className="mb-4 p-3 bg-[#0a0a0a] border-2 border-[#ffb000]/30">
                        <h4 className="text-sm font-bold mb-2 text-[#ffb000]">
                          武器スペック
                        </h4>
                        <div className="grid grid-cols-2 gap-2 text-sm text-[#00ff41]">
                          <div>
                            <span className="text-[#00ff41]/60">属性:</span>
                            <span className={`ml-2 font-bold ${
                              weapon.weapon.type === "BEAM" 
                                ? "text-[#00f0ff]" 
                                : "text-[#ffb000]"
                            }`}>
                              {weapon.weapon.type || "PHYSICAL"}
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">威力:</span>
                            <span className="ml-2 font-bold">{weapon.weapon.power}</span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">射程:</span>
                            <span className="ml-2 font-bold">{weapon.weapon.range}m</span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">命中率:</span>
                            <span className="ml-2 font-bold">{weapon.weapon.accuracy}%</span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">最適射程:</span>
                            <span className="ml-2 font-bold text-green-400">
                              {weapon.weapon.optimal_range || 300}m
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">減衰率:</span>
                            <span className="ml-2 font-bold">
                              {((weapon.weapon.decay_rate || 0.05) * 100).toFixed(1)}%
                            </span>
                          </div>
                          {weapon.weapon.max_ammo !== null && weapon.weapon.max_ammo !== undefined && (
                            <div>
                              <span className="text-[#00ff41]/60">弾数:</span>
                              <span className="ml-2 font-bold text-orange-400">
                                {weapon.weapon.max_ammo}
                              </span>
                            </div>
                          )}
                          {weapon.weapon.en_cost !== undefined && weapon.weapon.en_cost > 0 && (
                            <div>
                              <span className="text-[#00ff41]/60">EN消費:</span>
                              <span className="ml-2 font-bold text-cyan-400">
                                {weapon.weapon.en_cost}
                              </span>
                            </div>
                          )}
                          {weapon.weapon.cool_down_turn !== undefined && weapon.weapon.cool_down_turn > 0 && (
                            <div>
                              <span className="text-[#00ff41]/60">クールダウン:</span>
                              <span className="ml-2 font-bold text-pink-400">
                                {weapon.weapon.cool_down_turn}ターン
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Purchase Button */}
                      <SciFiButton
                        variant="secondary"
                        className="w-full"
                        onClick={() => handleWeaponPurchaseClick(weapon)}
                        disabled={!affordable}
                      >
                        {affordable ? "購入する (PURCHASE)" : "所持金不足 (INSUFFICIENT FUNDS)"}
                      </SciFiButton>
                    </SciFiCard>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* Confirmation Dialog for Mobile Suits */}
        {showConfirmDialog && selectedItem && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
            <SciFiPanel variant="secondary" chiseled={true}>
              <div className="p-8 max-w-md mx-4">
                <SciFiHeading level={3} className="mb-4" variant="secondary">
                  購入確認
                </SciFiHeading>
              
                {purchaseMessage ? (
                  <SciFiPanel 
                    variant={purchaseMessage.startsWith("エラー") ? "secondary" : "primary"}
                    chiseled={false}
                  >
                    <div className="p-4">
                      {purchaseMessage}
                    </div>
                  </SciFiPanel>
                ) : (
                  <>
                    <p className="mb-4 text-[#00ff41]">
                      <span className="font-bold text-[#ffb000]">
                        {selectedItem.name}
                      </span>
                      を
                      <span className="font-bold text-[#ffb000] mx-1">
                        {selectedItem.price.toLocaleString()} Credits
                      </span>
                      で購入しますか？
                    </p>

                    <div className="mb-6 p-3 bg-[#0a0a0a] border-2 border-[#ffb000]/30">
                      <div className="flex justify-between text-sm text-[#00ff41]">
                        <span className="text-[#00ff41]/60">現在の所持金:</span>
                        <span className="font-bold">{pilot?.credits.toLocaleString()} C</span>
                      </div>
                      <div className="flex justify-between text-sm mt-2 text-[#00ff41]">
                        <span className="text-[#00ff41]/60">購入後:</span>
                        <span className="font-bold text-[#00ff41]">
                          {((pilot?.credits || 0) - selectedItem.price).toLocaleString()} C
                        </span>
                      </div>
                    </div>

                    <div className="flex gap-4">
                      <SciFiButton
                        onClick={handleConfirmPurchase}
                        disabled={isPurchasing}
                        variant="secondary"
                        size="md"
                        className="flex-1"
                      >
                        {isPurchasing ? "処理中..." : "購入"}
                      </SciFiButton>
                      <SciFiButton
                        onClick={handleCancelPurchase}
                        disabled={isPurchasing}
                        variant="danger"
                        size="md"
                        className="flex-1"
                      >
                        キャンセル
                      </SciFiButton>
                    </div>
                  </>
                )}
              </div>
            </SciFiPanel>
          </div>
        )}

        {/* Confirmation Dialog for Weapons */}
        {showWeaponDialog && selectedWeapon && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
            <SciFiPanel variant="secondary" chiseled={true}>
              <div className="p-8 max-w-md mx-4">
                <SciFiHeading level={3} className="mb-4" variant="secondary">
                  武器購入確認
                </SciFiHeading>
              
                {purchaseMessage ? (
                  <SciFiPanel 
                    variant={purchaseMessage.startsWith("エラー") ? "secondary" : "primary"}
                    chiseled={false}
                  >
                    <div className="p-4">
                      {purchaseMessage}
                    </div>
                  </SciFiPanel>
                ) : (
                  <>
                    <p className="mb-4 text-[#00ff41]">
                      <span className="font-bold text-[#ffb000]">
                        {selectedWeapon.name}
                      </span>
                      を
                      <span className="font-bold text-[#ffb000] mx-1">
                        {selectedWeapon.price.toLocaleString()} Credits
                      </span>
                      で購入しますか？
                    </p>

                    <div className="mb-6 p-3 bg-[#0a0a0a] border-2 border-[#ffb000]/30">
                      <div className="flex justify-between text-sm text-[#00ff41]">
                        <span className="text-[#00ff41]/60">現在の所持金:</span>
                        <span className="font-bold">{pilot?.credits.toLocaleString()} C</span>
                      </div>
                      <div className="flex justify-between text-sm mt-2 text-[#00ff41]">
                        <span className="text-[#00ff41]/60">購入後:</span>
                        <span className="font-bold text-[#00ff41]">
                          {((pilot?.credits || 0) - selectedWeapon.price).toLocaleString()} C
                        </span>
                      </div>
                    </div>

                    <div className="flex gap-4">
                      <SciFiButton
                        onClick={handleConfirmWeaponPurchase}
                        disabled={isPurchasing}
                        variant="secondary"
                        size="md"
                        className="flex-1"
                      >
                        {isPurchasing ? "処理中..." : "購入"}
                      </SciFiButton>
                      <SciFiButton
                        onClick={handleCancelWeaponPurchase}
                        disabled={isPurchasing}
                        variant="danger"
                        size="md"
                        className="flex-1"
                      >
                        キャンセル
                      </SciFiButton>
                    </div>
                  </>
                )}
              </div>
            </SciFiPanel>
          </div>
        )}
      </div>
    </main>
  );
}
