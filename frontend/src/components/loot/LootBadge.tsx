/* frontend/src/components/loot/LootBadge.tsx */
import { LootItem } from "@/types/battle";
import { IconFileCertificate } from "@/components/icons/TablerIcons";
import { lootBadgeOf } from "@/utils/technology";

interface LootBadgeProps {
  loot: LootItem[] | null | undefined;
}

/**
 * バトル履歴の一覧で、戦利品のあったバトルに付けるバッジ。
 * 設計図の新規入手は NEW、技術Lvの上昇は LV UP、換金のみなら換金額の合計を表示する。
 */
export default function LootBadge({ loot }: LootBadgeProps) {
  const badge = lootBadgeOf(loot);
  if (!badge || !loot) return null;

  const names = loot.map((item) => item.target_name).join("、");

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-bold font-mono border ${
        badge.tone === "highlight"
          ? "border-[#00f0ff] text-[#00f0ff] bg-[#00f0ff]/10"
          : "border-[#ffb000]/50 text-[#ffb000] bg-[#ffb000]/5"
      }`}
      title={`戦利品: ${names}`}
      aria-label={`戦利品: ${names}`}
    >
      <IconFileCertificate className="w-3.5 h-3.5" />
      {badge.label}
    </span>
  );
}
