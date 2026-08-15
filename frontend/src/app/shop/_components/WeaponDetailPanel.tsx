/** 武器詳細表示パネル: モバイルではモーダル、PC ではインラインパネルとして機能する */
"use client";

import { SciFiPanel, SciFiHeading } from "@/components/ui";
import HoldSciFiButton from "@/components/ui/HoldSciFiButton";
import { WeaponListing } from "@/types/battle";
import { getWeaponRank, getRankColor } from "@/utils/rankUtils";
import { WEAPON_LABELS } from "@/utils/displayUtils";

interface WeaponDetailPanelProps {
  listing: WeaponListing;
  credits: number;
  isPurchasing: boolean;
  purchasingId: string | null;
  onPurchase: (id: string) => void;
  onClose?: () => void;
  isModal?: boolean;
}

export default function WeaponDetailPanel({
  listing,
  credits,
  isPurchasing,
  purchasingId,
  onPurchase,
  onClose,
  isModal = false,
}: WeaponDetailPanelProps) {
  const affordable = credits >= listing.price;
  const shortage = listing.price - credits;
  const remaining = credits - listing.price;

  const w = listing.weapon;
  const powerRank = w.power_rank ?? getWeaponRank("weapon_power", w.power);
  const rangeRank = w.range_rank ?? getWeaponRank("weapon_range", w.range);
  const accuracyRank = w.accuracy_rank ?? getWeaponRank("weapon_accuracy", w.accuracy);

  const content = (
    <div className="flex flex-col h-full">
      {/* ヘッダー */}
      <div className="flex items-start justify-between mb-4">
        <SciFiHeading level={3} variant="secondary" className="text-lg">
          {listing.name}
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

      {/* ランクバッジ */}
      <div className="mb-4 flex gap-4 text-xs font-mono">
        {[
          { label: WEAPON_LABELS.power, rank: powerRank },
          { label: WEAPON_LABELS.range, rank: rangeRank },
          { label: WEAPON_LABELS.accuracy, rank: accuracyRank },
        ].map(({ label, rank }) => (
          <div key={label}>
            <div className="text-[#00ff41]/60 mb-1">{label}</div>
            <div className={`font-bold text-lg ${getRankColor(rank)}`}>{rank}</div>
          </div>
        ))}
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

      {/* 購入ボタン */}
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
        <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
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
