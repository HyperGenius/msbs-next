/** コンパクト MS カード: 一覧ビュー用の横長カード（高さ ~80px） */
"use client";

import { SciFiCard } from "@/components/ui";
import { ShopListing } from "@/types/battle";
import { getRank, getRankColor } from "@/utils/rankUtils";
import { STATUS_LABELS, WEAPON_LABELS } from "@/utils/displayUtils";
import { getOptimalRangeLabel } from "@/utils/rankUtils";

interface MobileSuitCardProps {
  listing: ShopListing;
  credits: number;
  onSelect: (id: string) => void;
  isSelected?: boolean;
}

export default function MobileSuitCard({
  listing,
  credits,
  onSelect,
  isSelected,
}: MobileSuitCardProps) {
  const affordable = credits >= listing.price;
  const shortage = listing.price - credits;

  const hpRank = getRank("hp", listing.specs.max_hp);
  const armorRank = getRank("armor", listing.specs.armor);
  const mobilityRank = getRank("mobility", listing.specs.mobility);

  const mainWeapon = listing.specs.weapons?.[0];

  return (
    <SciFiCard
      variant={isSelected ? "accent" : affordable ? "secondary" : "primary"}
      interactive
      onClick={() => onSelect(listing.id)}
      className={`${affordable ? "" : "opacity-60"} cursor-pointer`}
    >
      <div className="py-1">
        {/* 行1: アイテム名 + 購入可/不足額バッジ */}
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
            <span className="text-[#00ff41]/50">{STATUS_LABELS.max_hp} </span>
            <span className={`font-bold ${getRankColor(hpRank)}`}>[{hpRank}]</span>
          </span>
          <span>
            <span className="text-[#00ff41]/50">{STATUS_LABELS.armor} </span>
            <span className={`font-bold ${getRankColor(armorRank)}`}>[{armorRank}]</span>
          </span>
          <span>
            <span className="text-[#00ff41]/50">{STATUS_LABELS.mobility} </span>
            <span className={`font-bold ${getRankColor(mobilityRank)}`}>[{mobilityRank}]</span>
          </span>
        </div>

        {/* 行3: 搭載武器 + 価格 */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-[#00ff41]/50 truncate mr-2">
            {mainWeapon ? (
              <>
                <span className="mr-1">{mainWeapon.name}</span>
                <span className={mainWeapon.type === "BEAM" ? "text-[#00f0ff]" : "text-[#ffb000]"}>
                  ({mainWeapon.type ?? "PHYSICAL"})
                </span>
                {mainWeapon.optimal_range !== undefined && (
                  <span className={`ml-1 ${getOptimalRangeLabel(mainWeapon.optimal_range).colorClass}`}>
                    {getOptimalRangeLabel(mainWeapon.optimal_range).label}
                  </span>
                )}
              </>
            ) : (
              <span className="text-[#00ff41]/30">—</span>
            )}
          </span>
          <span className="font-bold text-[#ffb000] shrink-0">
            {listing.price.toLocaleString()} C →
          </span>
        </div>
      </div>
    </SciFiCard>
  );
}
