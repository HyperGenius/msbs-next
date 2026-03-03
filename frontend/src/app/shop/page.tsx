/* frontend/src/app/shop/page.tsx */
"use client";

import { useState } from "react";
import { useShopListings, purchaseMobileSuit, usePilot, useWeaponListings, purchaseWeapon } from "@/services/api";
import { ShopListing, WeaponListing } from "@/types/battle";
import Link from "next/link";
import { SciFiPanel, SciFiButton, SciFiHeading, SciFiCard } from "@/components/ui";
import HoldSciFiButton from "@/components/ui/HoldSciFiButton";
import { getRankColor, getRank, getWeaponRank, getOptimalRangeLabel, getDecayRateRank } from "@/utils/rankUtils";
import { STATUS_LABELS, WEAPON_LABELS } from "@/utils/displayUtils";

type TabType = "mobile_suits" | "weapons";

export default function ShopPage() {
  const { listings, isLoading, isError } = useShopListings();
  const { weaponListings, isLoading: weaponsLoading, isError: weaponsError } = useWeaponListings();
  const { pilot, mutate: mutatePilot } = usePilot();
  const [activeTab, setActiveTab] = useState<TabType>("mobile_suits");
  const [isPurchasing, setIsPurchasing] = useState(false);
  const [purchasingId, setPurchasingId] = useState<string | null>(null);
  const [purchaseMessage, setPurchaseMessage] = useState<string | null>(null);

  const handleMobileSuitHoldComplete = async (item: ShopListing) => {
    if (isPurchasing) return;
    setIsPurchasing(true);
    setPurchasingId(item.id);
    setPurchaseMessage(null);

    try {
      const result = await purchaseMobileSuit(item.id);
      setPurchaseMessage(result.message);
      mutatePilot();
      setTimeout(() => {
        setPurchaseMessage(null);
      }, 3000);
    } catch (error) {
      if (error instanceof Error) {
        setPurchaseMessage(`エラー: ${error.message}`);
      } else {
        setPurchaseMessage("購入に失敗しました");
      }
      setTimeout(() => setPurchaseMessage(null), 3000);
    } finally {
      setIsPurchasing(false);
      setPurchasingId(null);
    }
  };

  const handleWeaponHoldComplete = async (weapon: WeaponListing) => {
    if (isPurchasing) return;
    setIsPurchasing(true);
    setPurchasingId(weapon.id);
    setPurchaseMessage(null);

    try {
      const result = await purchaseWeapon(weapon.id);
      setPurchaseMessage(result.message);
      mutatePilot();
      setTimeout(() => {
        setPurchaseMessage(null);
      }, 3000);
    } catch (error) {
      if (error instanceof Error) {
        setPurchaseMessage(`エラー: ${error.message}`);
      } else {
        setPurchaseMessage("購入に失敗しました");
      }
      setTimeout(() => setPurchaseMessage(null), 3000);
    } finally {
      setIsPurchasing(false);
      setPurchasingId(null);
    }
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
    <main className="min-h-screen bg-[#050505] text-[#00ff41] p-4 sm:p-6 md:p-8 font-mono">
      <div className="max-w-7xl mx-auto">

        {/* Page Title */}
        <div className="mb-4 sm:mb-8 border-b-2 border-[#ffb000]/30 pb-4">
          <div className="flex flex-col sm:flex-row gap-4 sm:gap-0 justify-between items-start sm:items-center">
            <div>
              <SciFiHeading level={2} variant="secondary" className="text-xl sm:text-2xl">
                {activeTab === "mobile_suits" ? "MOBILE SUIT SHOP" : "WEAPON SHOP"}
              </SciFiHeading>
              <p className="text-xs sm:text-sm text-[#ffb000]/60 ml-0 sm:ml-5">
                {activeTab === "mobile_suits" ? "モビルスーツ販売所" : "武器販売所"}
              </p>
            </div>
            <Link href="/garage" className="w-full sm:w-auto">
              <SciFiButton variant="primary" size="sm" className="w-full sm:w-auto">&lt; Back to Garage</SciFiButton>
            </Link>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="mb-4 sm:mb-6 flex flex-col sm:flex-row gap-2 sm:gap-4">
          <SciFiButton
            variant={activeTab === "mobile_suits" ? "secondary" : "primary"}
            onClick={() => setActiveTab("mobile_suits")}
            size="md"
            className="w-full sm:w-auto"
          >
            モビルスーツ (Mobile Suits)
          </SciFiButton>
          <SciFiButton
            variant={activeTab === "weapons" ? "secondary" : "primary"}
            onClick={() => setActiveTab("weapons")}
            size="md"
            className="w-full sm:w-auto"
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
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
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
                          <span className="text-[#00ff41]/60">{STATUS_LABELS.max_hp}:</span>
                          <span className={`ml-2 font-bold ${getRankColor(getRank("hp", item.specs.max_hp))}`}>
                            {getRank("hp", item.specs.max_hp)}
                          </span>
                        </div>
                        <div>
                          <span className="text-[#00ff41]/60">{STATUS_LABELS.armor}:</span>
                          <span className={`ml-2 font-bold ${getRankColor(getRank("armor", item.specs.armor))}`}>
                            {getRank("armor", item.specs.armor)}
                          </span>
                        </div>
                        <div>
                          <span className="text-[#00ff41]/60">{STATUS_LABELS.mobility}:</span>
                          <span className={`ml-2 font-bold ${getRankColor(getRank("mobility", item.specs.mobility))}`}>
                            {getRank("mobility", item.specs.mobility)}
                          </span>
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
                            <span className="text-[#00ff41]/60">{STATUS_LABELS.beam_resistance}:</span>
                            <span className="ml-2 font-bold text-[#00f0ff]">
                              {((item.specs.beam_resistance || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">{STATUS_LABELS.physical_resistance}:</span>
                            <span className="ml-2 font-bold text-[#ffb000]">
                              {((item.specs.physical_resistance || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Combat Aptitude */}
                      <div className="border-t-2 border-[#ffb000]/30 pt-2 mb-2">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span className="text-[#00ff41]/60">{STATUS_LABELS.melee_aptitude}:</span>
                            <span className="ml-1 font-bold text-red-400">
                              ×{(item.specs.melee_aptitude ?? 1.0).toFixed(1)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">{STATUS_LABELS.shooting_aptitude}:</span>
                            <span className="ml-1 font-bold text-[#00f0ff]">
                              ×{(item.specs.shooting_aptitude ?? 1.0).toFixed(1)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">{STATUS_LABELS.accuracy_bonus}:</span>
                            <span className="ml-1 font-bold text-green-400">
                              {(item.specs.accuracy_bonus ?? 0) >= 0 ? "+" : ""}{(item.specs.accuracy_bonus ?? 0).toFixed(1)}%
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">{STATUS_LABELS.evasion_bonus}:</span>
                            <span className="ml-1 font-bold text-yellow-400">
                              {(item.specs.evasion_bonus ?? 0) >= 0 ? "+" : ""}{(item.specs.evasion_bonus ?? 0).toFixed(1)}%
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">{STATUS_LABELS.acceleration_bonus}:</span>
                            <span className="ml-1 font-bold text-purple-400">
                              ×{(item.specs.acceleration_bonus ?? 1.0).toFixed(1)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">{STATUS_LABELS.turning_bonus}:</span>
                            <span className="ml-1 font-bold text-purple-400">
                              ×{(item.specs.turning_bonus ?? 1.0).toFixed(1)}
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
                                <span className="text-[#00ff41]/60">{WEAPON_LABELS.type}:</span>
                                <span className={`ml-1 font-bold ${
                                  item.specs.weapons[0].type === "BEAM" 
                                    ? "text-[#00f0ff]" 
                                    : "text-[#ffb000]"
                                }`}>
                                  {item.specs.weapons[0].type || "PHYSICAL"}
                                </span>
                              </div>
                              <div>
                                <span className="text-[#00ff41]/60">{WEAPON_LABELS.power}:</span>
                                <span className="ml-1 font-bold">
                                  {item.specs.weapons[0].power}
                                </span>
                              </div>
                              <div>
                                <span className="text-[#00ff41]/60">{WEAPON_LABELS.optimal_range}:</span>
                                <span className={`ml-1 font-bold ${getOptimalRangeLabel(item.specs.weapons[0].optimal_range || 300).colorClass}`}>
                                  {getOptimalRangeLabel(item.specs.weapons[0].optimal_range || 300).label} ({item.specs.weapons[0].optimal_range || 300}m)
                                </span>
                              </div>
                              <div>
                                <span className="text-[#00ff41]/60">{WEAPON_LABELS.accuracy}:</span>
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
                    {affordable ? (
                      <HoldSciFiButton
                        onHoldComplete={() => handleMobileSuitHoldComplete(item)}
                        disabled={isPurchasing && purchasingId !== item.id}
                        loading={purchasingId === item.id}
                        label="長押しで購入 (HOLD TO BUY)"
                        className="w-full"
                      />
                    ) : (
                      <SciFiButton
                        disabled
                        variant="danger"
                        size="md"
                        className="w-full"
                      >
                        購入不可
                      </SciFiButton>
                    )}
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
                            <span className="text-[#00ff41]/60">{WEAPON_LABELS.type}:</span>
                            <span className={`ml-2 font-bold ${
                              weapon.weapon.type === "BEAM" 
                                ? "text-[#00f0ff]" 
                                : "text-[#ffb000]"
                            }`}>
                              {weapon.weapon.type || "PHYSICAL"}
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">{WEAPON_LABELS.power}:</span>
                            <span className={`ml-2 font-bold ${getRankColor(weapon.weapon.power_rank ?? getWeaponRank("weapon_power", weapon.weapon.power))}`}>
                              {weapon.weapon.power_rank ?? getWeaponRank("weapon_power", weapon.weapon.power)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">{WEAPON_LABELS.range}:</span>
                            <span className={`ml-2 font-bold ${getRankColor(weapon.weapon.range_rank ?? getWeaponRank("weapon_range", weapon.weapon.range))}`}>
                              {weapon.weapon.range_rank ?? getWeaponRank("weapon_range", weapon.weapon.range)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">{WEAPON_LABELS.accuracy}:</span>
                            <span className={`ml-2 font-bold ${getRankColor(weapon.weapon.accuracy_rank ?? getWeaponRank("weapon_accuracy", weapon.weapon.accuracy))}`}>
                              {weapon.weapon.accuracy_rank ?? getWeaponRank("weapon_accuracy", weapon.weapon.accuracy)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">{WEAPON_LABELS.optimal_range}:</span>
                            <span className={`ml-2 font-bold ${getOptimalRangeLabel(weapon.weapon.optimal_range || 300).colorClass}`}>
                              {getOptimalRangeLabel(weapon.weapon.optimal_range || 300).label} ({weapon.weapon.optimal_range || 300}m)
                            </span>
                          </div>
                          <div>
                            <span className="text-[#00ff41]/60">{WEAPON_LABELS.decay_rate}:</span>
                            <span className={`ml-2 font-bold ${getRankColor(getDecayRateRank(weapon.weapon.decay_rate || 0.05))}`}>
                              {getDecayRateRank(weapon.weapon.decay_rate || 0.05)} ({((weapon.weapon.decay_rate || 0.05) * 100).toFixed(1)}%)
                            </span>
                          </div>
                          {weapon.weapon.max_ammo !== null && weapon.weapon.max_ammo !== undefined && (
                            <div>
                              <span className="text-[#00ff41]/60">{WEAPON_LABELS.max_ammo}:</span>
                              <span className="ml-2 font-bold text-orange-400">
                                {weapon.weapon.max_ammo}
                              </span>
                            </div>
                          )}
                          {weapon.weapon.en_cost !== undefined && weapon.weapon.en_cost > 0 && (
                            <div>
                              <span className="text-[#00ff41]/60">{WEAPON_LABELS.en_cost}:</span>
                              <span className="ml-2 font-bold text-cyan-400">
                                {weapon.weapon.en_cost}
                              </span>
                            </div>
                          )}
                          {weapon.weapon.cool_down_turn !== undefined && weapon.weapon.cool_down_turn > 0 && (
                            <div>
                              <span className="text-[#00ff41]/60">{WEAPON_LABELS.cool_down_turn}:</span>
                              <span className="ml-2 font-bold text-pink-400">
                                {weapon.weapon.cool_down_turn}ターン
                              </span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Purchase Button */}
                      {affordable ? (
                        <HoldSciFiButton
                          onHoldComplete={() => handleWeaponHoldComplete(weapon)}
                          disabled={isPurchasing && purchasingId !== weapon.id}
                          loading={purchasingId === weapon.id}
                          label="長押しで購入 (HOLD TO BUY)"
                          className="w-full"
                        />
                      ) : (
                        <SciFiButton
                          disabled
                          variant="danger"
                          className="w-full"
                        >
                          所持金不足 (INSUFFICIENT FUNDS)
                        </SciFiButton>
                      )}
                    </SciFiCard>
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* Purchase Result Toast */}
        {purchaseMessage && (
          <div className="fixed top-4 right-4 z-50 max-w-sm">
            <SciFiPanel
              variant={purchaseMessage.startsWith("エラー") ? "secondary" : "primary"}
              chiseled={false}
            >
              <div className="p-4 font-mono text-sm">
                {purchaseMessage}
              </div>
            </SciFiPanel>
          </div>
        )}
      </div>
    </main>
  );
}
