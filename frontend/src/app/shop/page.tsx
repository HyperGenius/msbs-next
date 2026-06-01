/* frontend/src/app/shop/page.tsx */
"use client";

import { useState } from "react";
import { useShopListings, purchaseMobileSuit, usePilot, useWeaponListings, purchaseWeapon } from "@/services/api";
import { ShopListing, WeaponListing } from "@/types/battle";
import { SciFiPanel } from "@/components/ui";
import ShopCreditHeader from "./_components/ShopCreditHeader";
import MobileSuitCard from "./_components/MobileSuitCard";
import WeaponCard from "./_components/WeaponCard";
import MobileSuitDetailPanel from "./_components/MobileSuitDetailPanel";
import WeaponDetailPanel from "./_components/WeaponDetailPanel";

type TabType = "mobile_suits" | "weapons";
type FilterType = "all" | "affordable";

export default function ShopPage() {
  const { listings, isLoading, isError } = useShopListings();
  const { weaponListings, isLoading: weaponsLoading, isError: weaponsError } = useWeaponListings();
  const { pilot, mutate: mutatePilot } = usePilot();

  const [activeTab, setActiveTab] = useState<TabType>("mobile_suits");
  const [filter, setFilter] = useState<FilterType>("all");
  const [selectedMsId, setSelectedMsId] = useState<string | null>(null);
  const [selectedWeaponId, setSelectedWeaponId] = useState<string | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isPurchasing, setIsPurchasing] = useState(false);
  const [purchasingId, setPurchasingId] = useState<string | null>(null);
  const [purchaseMessage, setPurchaseMessage] = useState<string | null>(null);

  const credits = pilot?.credits ?? 0;
  const canAfford = (price: number) => credits >= price;

  // フィルタリング後のアイテム一覧
  const visibleListings = filter === "affordable"
    ? listings?.filter((item) => canAfford(item.price))
    : listings;
  const visibleWeapons = filter === "affordable"
    ? weaponListings?.filter((w) => canAfford(w.price))
    : weaponListings;

  // 選択中アイテム（PC インラインパネル用）
  const selectedMs = listings?.find((item) => item.id === selectedMsId)
    ?? (visibleListings && visibleListings.length > 0 ? visibleListings[0] : null);
  const selectedWeapon = weaponListings?.find((w) => w.id === selectedWeaponId)
    ?? (visibleWeapons && visibleWeapons.length > 0 ? visibleWeapons[0] : null);

  const handleMsSelect = (id: string) => {
    setSelectedMsId(id);
    setIsDetailOpen(true);
  };

  const handleWeaponSelect = (id: string) => {
    setSelectedWeaponId(id);
    setIsDetailOpen(true);
  };

  const handleMobileSuitPurchase = async (itemId: string) => {
    if (isPurchasing) return;
    const item = listings?.find((i) => i.id === itemId);
    if (!item) return;
    setIsPurchasing(true);
    setPurchasingId(itemId);
    setPurchaseMessage(null);
    try {
      const result = await purchaseMobileSuit(itemId);
      setPurchaseMessage(result.message);
      mutatePilot();
      setIsDetailOpen(false);
      setTimeout(() => setPurchaseMessage(null), 3000);
    } catch (error) {
      setPurchaseMessage(error instanceof Error ? `エラー: ${error.message}` : "購入に失敗しました");
      setTimeout(() => setPurchaseMessage(null), 3000);
    } finally {
      setIsPurchasing(false);
      setPurchasingId(null);
    }
  };

  const handleWeaponPurchase = async (weaponId: string) => {
    if (isPurchasing) return;
    setIsPurchasing(true);
    setPurchasingId(weaponId);
    setPurchaseMessage(null);
    try {
      const result = await purchaseWeapon(weaponId);
      setPurchaseMessage(result.message);
      mutatePilot();
      setIsDetailOpen(false);
      setTimeout(() => setPurchaseMessage(null), 3000);
    } catch (error) {
      setPurchaseMessage(error instanceof Error ? `エラー: ${error.message}` : "購入に失敗しました");
      setTimeout(() => setPurchaseMessage(null), 3000);
    } finally {
      setIsPurchasing(false);
      setPurchasingId(null);
    }
  };

  if (isError || weaponsError) {
    return (
      <div className="min-h-screen bg-[#050505] text-[#00ff41] font-mono">
        <div className="max-w-7xl mx-auto p-8">
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
    <main className="min-h-screen bg-[#050505] text-[#00ff41] font-mono">
      {/* Sticky クレジットヘッダー */}
      <ShopCreditHeader
        credits={credits}
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setIsDetailOpen(false);
        }}
        filter={filter}
        onFilterChange={setFilter}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-4">
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
            {/* Mobile Suits タブ */}
            {activeTab === "mobile_suits" && (
              <div className="lg:flex lg:gap-6">
                {/* カードリスト */}
                <div className="lg:w-2/5 lg:overflow-y-auto lg:max-h-[calc(100vh-200px)]">
                  {visibleListings && visibleListings.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-3">
                      {visibleListings.map((item: ShopListing) => (
                        <MobileSuitCard
                          key={item.id}
                          listing={item}
                          credits={credits}
                          onSelect={handleMsSelect}
                          isSelected={selectedMs?.id === item.id}
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="text-[#00ff41]/40 text-sm text-center py-8">
                      {filter === "affordable" ? "現在の所持金で購入できるアイテムはありません" : "アイテムがありません"}
                    </p>
                  )}
                </div>

                {/* PC インライン詳細パネル */}
                {selectedMs && (
                  <div className="hidden lg:block lg:w-3/5 lg:sticky lg:top-[148px] lg:self-start">
                    <MobileSuitDetailPanel
                      listing={selectedMs}
                      credits={credits}
                      isPurchasing={isPurchasing}
                      purchasingId={purchasingId}
                      onPurchase={handleMobileSuitPurchase}
                      isModal={false}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Weapons タブ */}
            {activeTab === "weapons" && (
              <div className="lg:flex lg:gap-6">
                {/* カードリスト */}
                <div className="lg:w-2/5 lg:overflow-y-auto lg:max-h-[calc(100vh-200px)]">
                  {visibleWeapons && visibleWeapons.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-3">
                      {visibleWeapons.map((weapon: WeaponListing) => (
                        <WeaponCard
                          key={weapon.id}
                          listing={weapon}
                          credits={credits}
                          onSelect={handleWeaponSelect}
                          isSelected={selectedWeapon?.id === weapon.id}
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="text-[#00ff41]/40 text-sm text-center py-8">
                      {filter === "affordable" ? "現在の所持金で購入できるアイテムはありません" : "アイテムがありません"}
                    </p>
                  )}
                </div>

                {/* PC インライン詳細パネル */}
                {selectedWeapon && (
                  <div className="hidden lg:block lg:w-3/5 lg:sticky lg:top-[148px] lg:self-start">
                    <WeaponDetailPanel
                      listing={selectedWeapon}
                      credits={credits}
                      isPurchasing={isPurchasing}
                      purchasingId={purchasingId}
                      onPurchase={handleWeaponPurchase}
                      isModal={false}
                    />
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* モバイル: 詳細モーダル（MS） */}
      {isDetailOpen && activeTab === "mobile_suits" && selectedMs && (
        <MobileSuitDetailPanel
          listing={selectedMs}
          credits={credits}
          isPurchasing={isPurchasing}
          purchasingId={purchasingId}
          onPurchase={handleMobileSuitPurchase}
          onClose={() => setIsDetailOpen(false)}
          isModal
        />
      )}

      {/* モバイル: 詳細モーダル（武器） */}
      {isDetailOpen && activeTab === "weapons" && selectedWeapon && (
        <WeaponDetailPanel
          listing={selectedWeapon}
          credits={credits}
          isPurchasing={isPurchasing}
          purchasingId={purchasingId}
          onPurchase={handleWeaponPurchase}
          onClose={() => setIsDetailOpen(false)}
          isModal
        />
      )}

      {/* 購入結果トースト */}
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
    </main>
  );
}
