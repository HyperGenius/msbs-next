/** MS 詳細表示パネル: モバイルではモーダル、PC ではインラインパネルとして機能する */
"use client";

import { SciFiPanel, SciFiHeading } from "@/components/ui";
import SciFiProgress from "@/components/ui/SciFiProgress";
import HoldSciFiButton from "@/components/ui/HoldSciFiButton";
import { ShopListing } from "@/types/battle";
import { getRank, getRankColor, getOptimalRangeLabel } from "@/utils/rankUtils";
import { STATUS_LABELS, WEAPON_LABELS } from "@/utils/displayUtils";

interface MobileSuitDetailPanelProps {
  listing: ShopListing;
  credits: number;
  isPurchasing: boolean;
  purchasingId: string | null;
  onPurchase: (id: string) => void;
  onClose?: () => void;
  isModal?: boolean;
}

/** スペック値を 0〜100 の進捗率に正規化する */
const normalizeSpec = {
  hp: (v: number) => Math.min((v / 2000) * 100, 100),
  armor: (v: number) => Math.min(v, 100),
  mobility: (v: number) => Math.min((v / 2.0) * 100, 100),
  sensor_range: (v: number) => Math.min((v / 600) * 100, 100),
};

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
  const mainWeapon = listing.specs.weapons?.[0];

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

      {/* 説明文 */}
      {listing.description && (
        <p className="text-sm text-[#00ff41]/60 mb-4 border-b border-[#00ff41]/20 pb-3">
          {listing.description}
        </p>
      )}

      {/* スペックバー */}
      <div className="mb-4 space-y-3">
        {[
          { label: STATUS_LABELS.max_hp, value: listing.specs.max_hp, rank: getRank("hp", listing.specs.max_hp), normalize: normalizeSpec.hp },
          { label: STATUS_LABELS.armor, value: listing.specs.armor, rank: getRank("armor", listing.specs.armor), normalize: normalizeSpec.armor },
          { label: STATUS_LABELS.mobility, value: listing.specs.mobility, rank: getRank("mobility", listing.specs.mobility), normalize: normalizeSpec.mobility },
          ...(listing.specs.sensor_range !== undefined
            ? [{ label: STATUS_LABELS.sensor_range, value: listing.specs.sensor_range, rank: getRank("hp", listing.specs.sensor_range), normalize: normalizeSpec.sensor_range }]
            : []),
        ].map(({ label, value, rank, normalize }) => (
          <div key={label}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-[#00ff41]/60">{label}</span>
              <div className="flex items-center gap-2">
                <span className="text-[#00ff41]/80">{value}</span>
                <span className={`font-bold text-sm ${getRankColor(rank)}`}>[{rank}]</span>
              </div>
            </div>
            <SciFiProgress value={normalize(value)} />
          </div>
        ))}
      </div>

      {/* 搭載武器 */}
      {mainWeapon && (
        <div className="mb-4 p-3 bg-[#0a0a0a] border border-[#ffb000]/30">
          <div className="text-xs font-bold text-[#ffb000] mb-2">MAIN WEAPON</div>
          <div className="text-sm font-bold text-[#00ff41] mb-2">{mainWeapon.name}</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <div>
              <span className="text-[#00ff41]/50">{WEAPON_LABELS.type}: </span>
              <span className={`font-bold ${mainWeapon.type === "BEAM" ? "text-[#00f0ff]" : "text-[#ffb000]"}`}>
                {mainWeapon.type ?? "PHYSICAL"}
              </span>
            </div>
            {mainWeapon.optimal_range !== undefined && (
              <div>
                <span className="text-[#00ff41]/50">{WEAPON_LABELS.optimal_range}: </span>
                <span className={`font-bold ${getOptimalRangeLabel(mainWeapon.optimal_range).colorClass}`}>
                  {getOptimalRangeLabel(mainWeapon.optimal_range).label}
                </span>
              </div>
            )}
            <div>
              <span className="text-[#00ff41]/50">{WEAPON_LABELS.power}: </span>
              <span className="font-bold text-[#00ff41]">{mainWeapon.power}</span>
            </div>
            <div>
              <span className="text-[#00ff41]/50">{WEAPON_LABELS.accuracy}: </span>
              <span className="font-bold text-[#00ff41]">{mainWeapon.accuracy}%</span>
            </div>
          </div>
        </div>
      )}

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
        className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
        onClick={(e) => {
          if (e.target === e.currentTarget) onClose?.();
        }}
      >
        {/* 背景オーバーレイ */}
        <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />

        {/* モーダル本体 */}
        <div className="relative z-10 w-full sm:max-w-lg max-h-[92vh] sm:max-h-[85vh] overflow-y-auto">
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
