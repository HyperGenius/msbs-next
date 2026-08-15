/** コンパクト武器カード: 一覧ビュー用の横長カード */
"use client";

import { SciFiCard } from "@/components/ui";
import { WeaponListing } from "@/types/battle";
import { getWeaponRank, getRankColor } from "@/utils/rankUtils";
import { WEAPON_LABELS } from "@/utils/displayUtils";

interface WeaponCardProps {
  listing: WeaponListing;
  credits: number;
  onSelect: (id: string) => void;
  isSelected?: boolean;
}

export default function WeaponCard({
  listing,
  credits,
  onSelect,
  isSelected,
}: WeaponCardProps) {
  const affordable = credits >= listing.price;
  const shortage = listing.price - credits;

  const powerRank = listing.weapon.power_rank ?? getWeaponRank("weapon_power", listing.weapon.power);
  const rangeRank = listing.weapon.range_rank ?? getWeaponRank("weapon_range", listing.weapon.range);
  const accuracyRank = listing.weapon.accuracy_rank ?? getWeaponRank("weapon_accuracy", listing.weapon.accuracy);

  return (
    <SciFiCard
      variant={isSelected ? "accent" : affordable ? "secondary" : "primary"}
      interactive={affordable}
      onClick={affordable ? () => onSelect(listing.id) : undefined}
      className={
        affordable
          ? "cursor-pointer"
          : "opacity-50 grayscale cursor-not-allowed"
      }
    >
      <div className="py-1">
        {/* 行1: 武器名 + 購入クレジット数 */}
        <div className="flex items-center justify-between mb-1">
          <span className="font-bold text-[#ffb000] text-sm truncate mr-2">
            {listing.name}
          </span>
          <span className={`font-bold text-xs shrink-0 ${affordable ? "text-[#ffb000]" : "text-red-400"}`}>
            {listing.price.toLocaleString()} C
            {!affordable && ` (-${shortage.toLocaleString()})`}
          </span>
        </div>

        {/* 行2: ランクバッジ */}
        <div className="flex items-center gap-3 mb-1 text-xs font-mono">
          <span>
            <span className="text-[#00ff41]/50">{WEAPON_LABELS.power} </span>
            <span className={`font-bold ${getRankColor(powerRank)}`}>[{powerRank}]</span>
          </span>
          <span>
            <span className="text-[#00ff41]/50">{WEAPON_LABELS.range} </span>
            <span className={`font-bold ${getRankColor(rangeRank)}`}>[{rangeRank}]</span>
          </span>
          <span>
            <span className="text-[#00ff41]/50">{WEAPON_LABELS.accuracy} </span>
            <span className={`font-bold ${getRankColor(accuracyRank)}`}>[{accuracyRank}]</span>
          </span>
        </div>

        {/* 行3: フレーバーテキスト */}
        {listing.flavor_text && (
          <p className="text-xs text-[#00ff41]/50 italic line-clamp-2">
            {listing.flavor_text}
          </p>
        )}
      </div>
    </SciFiCard>
  );
}
