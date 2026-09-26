/* frontend/src/components/loot/LootItemCard.tsx */
import { LootItem } from "@/types/battle";
import { IconFileCertificate } from "@/components/icons/TablerIcons";

/** 設計図の対象の種別ラベル */
export const LOOT_TARGET_LABELS: Record<LootItem["target_type"], string> = {
  MOBILE_SUIT: "機体設計図",
  WEAPON: "武器設計図",
};

interface LootItemCardProps {
  item: LootItem;
  /** 新規入手のときに、入手演出（光の走査）を再生する */
  animate?: boolean;
}

/**
 * 戦利品1件を表示するカード。
 * 新規入手はシアンで強調し、所持済みの換金はアンバーでクレジットを示す。
 */
export default function LootItemCard({
  item,
  animate = false,
}: LootItemCardProps) {
  const isNew = item.is_new;
  const tone = isNew
    ? "border-[#00f0ff] bg-[#00f0ff]/10 text-[#00f0ff]"
    : "border-[#ffb000]/40 bg-[#ffb000]/5 text-[#ffb000]";

  return (
    <div
      className={`relative overflow-hidden flex items-center gap-3 border px-3 py-2 font-mono ${tone} ${
        isNew && animate ? "loot-new-reveal" : ""
      }`}
      data-testid="loot-item"
    >
      {isNew && animate && (
        <span
          aria-hidden="true"
          className="loot-new-sweep pointer-events-none absolute inset-y-0 -left-1/3 w-1/3"
        />
      )}
      <IconFileCertificate className="w-7 h-7 shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[10px] tracking-widest opacity-70">
          <span>{LOOT_TARGET_LABELS[item.target_type]}</span>
        </div>
        <p
          className="text-sm sm:text-base font-bold text-white truncate"
          title={item.target_name}
        >
          {item.target_name}
        </p>
        <p className="text-[11px] opacity-80">
          {isNew
            ? "ショップで購入できるようになりました"
            : `所持済みのため +${item.credits_awarded.toLocaleString()} C に換金`}
        </p>
      </div>
      {isNew ? (
        <span className="shrink-0 bg-[#00f0ff] text-black text-xs font-bold px-2 py-0.5 tracking-widest">
          NEW
        </span>
      ) : (
        <span className="shrink-0 text-sm font-bold">
          +{item.credits_awarded.toLocaleString()} C
        </span>
      )}
    </div>
  );
}
