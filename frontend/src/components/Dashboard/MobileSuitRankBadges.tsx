import { MobileSuit } from "@/types/battle";
import { STATUS_LABELS } from "@/utils/displayUtils";
import {
  getMobileSuitRanks,
  getRankColor,
  MobileSuitRanks,
} from "@/utils/rankUtils";

const RANK_ITEMS: { label: string; key: keyof MobileSuitRanks }[] = [
  { label: STATUS_LABELS.hp, key: "hp" },
  { label: STATUS_LABELS.armor, key: "armor" },
  { label: STATUS_LABELS.mobility, key: "mobility" },
];

interface MobileSuitRankBadgesProps {
  mobileSuit: MobileSuit;
  /** 文字サイズなどの追加クラス */
  className?: string;
}

/** 機体の HP・装甲・機動性ランクを横並びで表示する */
export default function MobileSuitRankBadges({
  mobileSuit,
  className = "text-sm",
}: MobileSuitRankBadgesProps) {
  const ranks = getMobileSuitRanks(mobileSuit);
  return (
    <div className={`flex gap-3 ${className}`}>
      {RANK_ITEMS.map(({ label, key }) => (
        <span key={key} className="flex items-center gap-1 text-gray-400">
          {label}:
          <span className={`font-bold ${getRankColor(ranks[key])}`}>
            {ranks[key]}
          </span>
        </span>
      ))}
    </div>
  );
}
