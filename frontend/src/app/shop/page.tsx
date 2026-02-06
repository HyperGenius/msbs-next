/* frontend/src/app/shop/page.tsx */
"use client";

import { useState } from "react";
import { useShopListings, purchaseMobileSuit, usePilot } from "@/services/api";
import { ShopListing } from "@/types/battle";
import Link from "next/link";
import Header from "@/components/Header";

export default function ShopPage() {
  const { listings, isLoading, isError } = useShopListings();
  const { pilot, mutate: mutatePilot } = usePilot();
  const [selectedItem, setSelectedItem] = useState<ShopListing | null>(null);
  const [isPurchasing, setIsPurchasing] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
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

  const canAfford = (price: number): boolean => {
    return pilot ? pilot.credits >= price : false;
  };

  if (isError) {
    return (
      <div className="min-h-screen bg-gray-900 text-green-400 p-8 font-mono">
        <div className="max-w-7xl mx-auto">
          <p className="text-red-500">データの取得に失敗しました。</p>
          <p className="text-sm mt-2">Backendが起動しているか確認してください。</p>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gray-900 text-green-400 p-8 font-mono">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <Header />

        {/* Page Title */}
        <div className="mb-8 border-b border-green-700 pb-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold">MOBILE SUIT SHOP</h2>
              <p className="text-sm opacity-70">モビルスーツ販売所</p>
            </div>
            <Link
              href="/garage"
              className="px-4 py-2 bg-green-900 hover:bg-green-800 rounded font-bold transition-colors"
            >
              &lt; Back to Garage
            </Link>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <p className="text-xl animate-pulse">LOADING INVENTORY...</p>
          </div>
        ) : (
          <>
            {/* Shop Items Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {listings?.map((item) => {
                const affordable = canAfford(item.price);
                
                return (
                  <div
                    key={item.id}
                    className={`bg-gray-800 p-6 rounded-lg border transition-all ${
                      affordable
                        ? "border-green-800 hover:border-green-600"
                        : "border-red-900 opacity-60"
                    }`}
                  >
                    {/* Item Header */}
                    <div className="mb-4">
                      <h3 className="text-xl font-bold text-green-300 mb-2">
                        {item.name}
                      </h3>
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-2xl font-bold text-yellow-400">
                          {item.price.toLocaleString()} C
                        </span>
                        {!affordable && (
                          <span className="text-sm text-red-400 font-bold">
                            所持金不足
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-400">{item.description}</p>
                    </div>

                    {/* Specs */}
                    <div className="mb-4 p-3 bg-gray-900 rounded border border-green-900">
                      <h4 className="text-sm font-bold mb-2 text-green-500">
                        SPECIFICATIONS
                      </h4>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div>
                          <span className="text-gray-400">HP:</span>
                          <span className="ml-2 font-bold">{item.specs.max_hp}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">装甲:</span>
                          <span className="ml-2 font-bold">{item.specs.armor}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">機動性:</span>
                          <span className="ml-2 font-bold">{item.specs.mobility}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">武器:</span>
                          <span className="ml-2 font-bold">
                            {item.specs.weapons[0]?.name || "N/A"}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Purchase Button */}
                    <button
                      onClick={() => handlePurchaseClick(item)}
                      disabled={!affordable || isPurchasing}
                      className={`w-full px-4 py-3 rounded font-bold text-black transition-colors ${
                        affordable && !isPurchasing
                          ? "bg-green-500 hover:bg-green-400 cursor-pointer"
                          : "bg-gray-600 cursor-not-allowed"
                      }`}
                    >
                      {affordable ? "購入する (BUY)" : "購入不可"}
                    </button>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* Confirmation Dialog */}
        {showConfirmDialog && selectedItem && (
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
            <div className="bg-gray-800 p-8 rounded-lg border-2 border-green-500 max-w-md w-full mx-4">
              <h3 className="text-xl font-bold mb-4 text-green-300">
                購入確認
              </h3>
              
              {purchaseMessage ? (
                <div className={`p-4 rounded mb-4 ${
                  purchaseMessage.startsWith("エラー")
                    ? "bg-red-900/50 border border-red-500 text-red-300"
                    : "bg-green-900/50 border border-green-500 text-green-300"
                }`}>
                  {purchaseMessage}
                </div>
              ) : (
                <>
                  <p className="mb-4">
                    <span className="font-bold text-yellow-400">
                      {selectedItem.name}
                    </span>
                    を
                    <span className="font-bold text-yellow-400 mx-1">
                      {selectedItem.price.toLocaleString()} Credits
                    </span>
                    で購入しますか？
                  </p>

                  <div className="mb-6 p-3 bg-gray-900 rounded">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">現在の所持金:</span>
                      <span className="font-bold">{pilot?.credits.toLocaleString()} C</span>
                    </div>
                    <div className="flex justify-between text-sm mt-2">
                      <span className="text-gray-400">購入後:</span>
                      <span className="font-bold text-green-400">
                        {((pilot?.credits || 0) - selectedItem.price).toLocaleString()} C
                      </span>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <button
                      onClick={handleConfirmPurchase}
                      disabled={isPurchasing}
                      className={`flex-1 px-4 py-3 rounded font-bold transition-colors ${
                        isPurchasing
                          ? "bg-gray-600 cursor-not-allowed text-gray-400"
                          : "bg-green-500 hover:bg-green-400 text-black"
                      }`}
                    >
                      {isPurchasing ? "処理中..." : "購入"}
                    </button>
                    <button
                      onClick={handleCancelPurchase}
                      disabled={isPurchasing}
                      className="flex-1 px-4 py-3 bg-gray-700 hover:bg-gray-600 rounded font-bold transition-colors"
                    >
                      キャンセル
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
