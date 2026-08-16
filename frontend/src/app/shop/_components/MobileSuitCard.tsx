/** コンパクト MS カード: 一覧ビュー用の横長カード */
"use client";

import { SciFiCard } from "@/components/ui";
import { ShopListing } from "@/types/battle";
import { getRank, getRankColor } from "@/utils/rankUtils";
import { STATUS_LABELS, getMobileSuitShopLabel } from "@/utils/displayUtils";

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

  return (
    <SciFiCard
      variant={isSelected ? "accent" : affordable ? "secondary" : "primary"}
      interactive
      onClick={() => onSelect(listing.id)}
      className={`${affordable ? "" : "opacity-60"} cursor-pointer`}
    >
      <div className="py-1">
        {/* 行1: ラベル({model_number} {name_ja}) + 購入クレジット数 */}
        <div className="flex items-center justify-between mb-1">
          <span className="font-bold text-[#ffb000] text-sm truncate mr-2">
            {getMobileSuitShopLabel(listing)}
          </span>
          <span className={`font-bold text-xs shrink-0 ${affordable ? "text-[#ffb000]" : "text-red-400"}`}>
            {listing.price.toLocaleString()} C
            {!affordable && ` (-${shortage.toLocaleString()})`}
          </span>
        </div>

        {/* 行2: ランクバッジ */}
        <div className="flex items-center gap-3 mb-1 text-xs font-mono">
          <span>
            <span className="text-[#00ff41]/50">{STATUS_LABELS.max_hp} </span>
            <span className={`font-bold ${getRankColor(hpRank)}`}>{hpRank}</span>
          </span>
          <span>
            <span className="text-[#00ff41]/50">{STATUS_LABELS.armor} </span>
            <span className={`font-bold ${getRankColor(armorRank)}`}>{armorRank}</span>
          </span>
          <span>
            <span className="text-[#00ff41]/50">{STATUS_LABELS.mobility} </span>
            <span className={`font-bold ${getRankColor(mobilityRank)}`}>{mobilityRank}</span>
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
