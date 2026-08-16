/** MS 詳細表示パネル: モバイルではモーダル、PC ではインラインパネルとして機能する */
"use client";

import { SciFiPanel, SciFiHeading } from "@/components/ui";
import HoldSciFiButton from "@/components/ui/HoldSciFiButton";
import MobileSuitStatRadar from "./MobileSuitStatRadar";
import { ShopListing } from "@/types/battle";
import { getMobileSuitShopLabel } from "@/utils/displayUtils";

interface MobileSuitDetailPanelProps {
  listing: ShopListing;
  credits: number;
  isPurchasing: boolean;
  purchasingId: string | null;
  onPurchase: (id: string) => void;
  onClose?: () => void;
  isModal?: boolean;
}

export default function MobileSuitDetailPanel({
  listing,
  credits,
  isPurchasing,
  purchasingId,
  onPurchase,
  onClose,
  isModal = false,
}: MobileSuitDetailPanelProps) {
  const affordable = credits >= listing.price;
  const shortage = listing.price - credits;
  const remaining = credits - listing.price;
  const label = getMobileSuitShopLabel(listing);

  const content = (
    <div className="flex flex-col h-full">
      {/* ヘッダー */}
      <div className="flex items-start justify-between mb-4">
        <SciFiHeading level={3} variant="secondary" className="text-lg">
          {label}
        </SciFiHeading>
        {isModal && onClose && (
          <button
            onClick={onClose}
            className="text-[#00ff41]/60 hover:text-[#00ff41] text-xl font-bold ml-4 shrink-0"
            aria-label="閉じる"
          >
            ×
          </button>
        )}
      </div>

      {/* フレーバーテキスト */}
      {listing.flavor_text && (
        <p className="text-sm text-[#00ff41]/60 italic mb-4 border-b border-[#00ff41]/20 pb-3">
          {listing.flavor_text}
        </p>
      )}

      {/* スペックレーダーチャート */}
      <div className="mb-4">
        <MobileSuitStatRadar specs={listing.specs} name={label} />
      </div>

      {/* ビームジェネレータLv・武器スロット数 */}
      <div className="mb-4 flex flex-wrap gap-x-4 gap-y-1 text-xs font-mono">
        <div>
          <span className="text-[#00ff41]/50">ビームジェネレータLv: </span>
          <span className="font-bold text-[#00f0ff]">{listing.beam_generator_lv}</span>
        </div>
        <div>
          <span className="text-[#00ff41]/50">武器スロット数: </span>
          <span className="font-bold text-[#00ff41]">{listing.weapon_slot_count}</span>
        </div>
      </div>

      {/* 価格サマリー */}
      <div className="mb-4 p-3 bg-[#0a0a0a] border border-[#00ff41]/20 text-sm font-mono space-y-1">
        <div className="flex justify-between">
          <span className="text-[#00ff41]/50">所持金</span>
          <span className="text-[#00ff41]">{credits.toLocaleString()} C</span>
        </div>
        <div className="flex justify-between">
          <span className="text-[#00ff41]/50">価格</span>
          <span className="text-[#ffb000]">{listing.price.toLocaleString()} C</span>
        </div>
        <div className="flex justify-between border-t border-[#00ff41]/20 pt-1">
          <span className="text-[#00ff41]/50">残高</span>
          <span className={`font-bold ${affordable ? "text-[#00ff41]" : "text-red-400"}`}>
            {affordable ? `${remaining.toLocaleString()} C ✓` : `-${shortage.toLocaleString()} C`}
          </span>
        </div>
      </div>

      {/* 購入ボタン（スペーサーで下部に押し出す） */}
      <div className="mt-auto">
        {!affordable && (
          <p className="text-xs text-red-400 text-center mb-2">
            所持金不足（-{shortage.toLocaleString()} C）
          </p>
        )}
        {affordable ? (
          <HoldSciFiButton
            onHoldComplete={() => onPurchase(listing.id)}
            disabled={isPurchasing && purchasingId !== listing.id}
            loading={purchasingId === listing.id}
            label="長押しで購入 (HOLD TO BUY)"
            className="w-full"
          />
        ) : (
          <div className="w-full py-3 text-center text-sm font-mono bg-[#0a0a0a] border border-red-900/50 text-red-500">
            購入不可 (INSUFFICIENT FUNDS)
          </div>
        )}
      </div>
    </div>
  );

  if (isModal) {
    return (
      <div
        // z-[60] で BottomNav(z-50) の上に重ねる。p-4 で上下均等マージンを確保
        className="fixed inset-0 z-[60] flex items-center justify-center p-4"
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose?.();
        }}
      >
        {/* 背景オーバーレイ */}
        <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />

        {/* モーダル本体 */}
        <div className="relative z-10 w-full max-w-lg max-h-[85vh] overflow-y-auto">
          <SciFiPanel variant="secondary" scanline>
            <div className="p-4 sm:p-6">
              {content}
            </div>
          </SciFiPanel>
        </div>
      </div>
    );
  }

  return (
    <SciFiPanel variant="secondary" scanline>
      <div className="p-4 sm:p-6 h-full">
        {content}
      </div>
    </SciFiPanel>
  );
}
