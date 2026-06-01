/** 武器詳細表示パネル: モバイルではモーダル、PC ではインラインパネルとして機能する */
"use client";

import { SciFiPanel, SciFiHeading } from "@/components/ui";
import SciFiProgress from "@/components/ui/SciFiProgress";
import HoldSciFiButton from "@/components/ui/HoldSciFiButton";
import { WeaponListing } from "@/types/battle";
import { getWeaponRank, getRankColor, getOptimalRangeLabel, getDecayRateRank } from "@/utils/rankUtils";
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

/** 武器スペック値を 0〜100 の進捗率に正規化する */
const normalizeWeapon = {
  power: (v: number) => Math.min((v / 300) * 100, 100),
  range: (v: number) => Math.min((v / 600) * 100, 100),
  accuracy: (v: number) => Math.min((v / 90) * 100, 100),
};

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
  const decayRank = getDecayRateRank(w.decay_rate ?? 0.05);
  const optRange = w.optimal_range !== undefined ? getOptimalRangeLabel(w.optimal_range) : null;

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

      {/* 属性・適正距離 */}
      <div className="flex gap-3 mb-4 text-xs font-mono">
        <div>
          <span className="text-[#00ff41]/50">{WEAPON_LABELS.type}: </span>
          <span className={`font-bold ${w.type === "BEAM" ? "text-[#00f0ff]" : "text-[#ffb000]"}`}>
            {w.type ?? "PHYSICAL"}
          </span>
        </div>
        {optRange && (
          <div>
            <span className="text-[#00ff41]/50">{WEAPON_LABELS.optimal_range}: </span>
            <span className={`font-bold ${optRange.colorClass}`}>{optRange.label}</span>
          </div>
        )}
        <div>
          <span className="text-[#00ff41]/50">{WEAPON_LABELS.decay_rate}: </span>
          <span className={`font-bold ${getRankColor(decayRank)}`}>[{decayRank}]</span>
        </div>
      </div>

      {/* スペックバー */}
      <div className="mb-4 space-y-3">
        {[
          { label: WEAPON_LABELS.power, value: w.power, rank: powerRank, normalize: normalizeWeapon.power },
          { label: WEAPON_LABELS.range, value: w.range, rank: rangeRank, normalize: normalizeWeapon.range },
          { label: WEAPON_LABELS.accuracy, value: w.accuracy, rank: accuracyRank, normalize: normalizeWeapon.accuracy },
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

      {/* オプションフラグ */}
      {(w.max_ammo !== null && w.max_ammo !== undefined) || (w.en_cost !== undefined && w.en_cost > 0) || (w.cool_down_turn !== undefined && w.cool_down_turn > 0) ? (
        <div className="mb-4 flex gap-3 text-xs font-mono">
          {w.max_ammo !== null && w.max_ammo !== undefined && (
            <div>
              <span className="text-[#00ff41]/50">{WEAPON_LABELS.max_ammo}: </span>
              <span className="font-bold text-orange-400">{w.max_ammo}</span>
            </div>
          )}
          {w.en_cost !== undefined && w.en_cost > 0 && (
            <div>
              <span className="text-[#00ff41]/50">{WEAPON_LABELS.en_cost}: </span>
              <span className="font-bold text-cyan-400">{w.en_cost}</span>
            </div>
          )}
          {w.cool_down_turn !== undefined && w.cool_down_turn > 0 && (
            <div>
              <span className="text-[#00ff41]/50">{WEAPON_LABELS.cool_down_turn}: </span>
              <span className="font-bold text-pink-400">{w.cool_down_turn}T</span>
            </div>
          )}
        </div>
      ) : null}

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
