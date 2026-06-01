/** コンパクト武器カード: 一覧ビュー用の横長カード */
"use client";

import { SciFiCard } from "@/components/ui";
import { WeaponListing } from "@/types/battle";
import { getWeaponRank, getRankColor, getOptimalRangeLabel } from "@/utils/rankUtils";
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

  const optRange = listing.weapon.optimal_range !== undefined
    ? getOptimalRangeLabel(listing.weapon.optimal_range)
    : null;

  const hasEnCost = listing.weapon.en_cost !== undefined && listing.weapon.en_cost > 0;
  const hasAmmo = listing.weapon.max_ammo !== null && listing.weapon.max_ammo !== undefined;

  return (
    <SciFiCard
      variant={isSelected ? "accent" : affordable ? "secondary" : "primary"}
      interactive
      onClick={() => onSelect(listing.id)}
      className={`${affordable ? "" : "opacity-60"} cursor-pointer`}
    >
      <div className="py-1">
        {/* 行1: 武器名 + 購入可/不足額バッジ */}
        <div className="flex items-center justify-between mb-1">
          <span className="font-bold text-[#ffb000] text-sm truncate mr-2">
            {listing.name}
          </span>
          {affordable ? (
            <span className="text-xs font-bold text-[#00ff41] border border-[#00ff41]/50 px-1.5 py-0.5 shrink-0">
              購入可
            </span>
          ) : (
            <span className="text-xs font-bold text-red-400 shrink-0">
              -{shortage.toLocaleString()} C
            </span>
          )}
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

        {/* 行3: 属性・適正距離・フラグ + 価格 */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-[#00ff41]/50 flex items-center gap-1.5 truncate mr-2">
            <span className={listing.weapon.type === "BEAM" ? "text-[#00f0ff]" : "text-[#ffb000]"}>
              {listing.weapon.type ?? "PHYSICAL"}
            </span>
            {optRange && (
              <span className={optRange.colorClass}>{optRange.label}</span>
            )}
            {hasAmmo && <span className="text-orange-400">弾数有</span>}
            {hasEnCost && <span className="text-cyan-400">EN有</span>}
          </span>
          <span className="font-bold text-[#ffb000] shrink-0">
            {listing.price.toLocaleString()} C →
          </span>
        </div>
      </div>
    </SciFiCard>
  );
}
