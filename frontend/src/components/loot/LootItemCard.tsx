/* frontend/src/components/loot/LootItemCard.tsx */
import { BlueprintLootItem, LootItem, TechFragmentLootItem } from "@/types/battle";
import { IconCpu, IconFileCertificate } from "@/components/icons/TablerIcons";
import { isHighlightedLoot, techFragmentLootMessage } from "@/utils/technology";

/** 設計図の対象の種別ラベル */
export const LOOT_TARGET_LABELS: Record<BlueprintLootItem["target_type"], string> = {
  MOBILE_SUIT: "機体設計図",
  WEAPON: "武器設計図",
};

export const TECH_FRAGMENT_LABEL = "技術断片";

interface LootItemCardProps {
  item: LootItem;
  /** 新規入手・技術Lvの上昇のときに、入手演出（光の走査）を再生する */
  animate?: boolean;
}

/**
 * 戦利品1件を表示するカード。
 * 設計図の新規入手と技術Lvの上昇はシアンで強調し、換金はアンバーでクレジットを示す。
 * それ以外の技術断片は緑で累計数を示す。
 */
export default function LootItemCard({ item, animate = false }: LootItemCardProps) {
  const highlighted = isHighlightedLoot(item);
  const tone = highlighted
    ? "border-[#00f0ff] bg-[#00f0ff]/10 text-[#00f0ff]"
    : item.credits_awarded > 0
      ? "border-[#ffb000]/40 bg-[#ffb000]/5 text-[#ffb000]"
      : "border-[#00ff41]/40 bg-[#00ff41]/5 text-[#00ff41]";
  const Icon = item.kind === "BLUEPRINT" ? IconFileCertificate : IconCpu;

  return (
    <div
      className={`relative overflow-hidden flex items-center gap-3 border px-3 py-2 font-mono ${tone} ${
        highlighted && animate ? "loot-new-reveal" : ""
      }`}
      data-testid="loot-item"
    >
      {highlighted && animate && (
        <span
          aria-hidden="true"
          className="loot-new-sweep pointer-events-none absolute inset-y-0 -left-1/3 w-1/3"
        />
      )}
      <Icon className="w-7 h-7 shrink-0" />
      {item.kind === "BLUEPRINT" ? (
        <BlueprintLootBody item={item} />
      ) : (
        <TechFragmentLootBody item={item} />
      )}
    </div>
  );
}

/** 設計図の戦利品の本文と右端の表示 */
function BlueprintLootBody({ item }: { item: BlueprintLootItem }) {
  return (
    <>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[10px] tracking-widest opacity-70">
          <span>{LOOT_TARGET_LABELS[item.target_type]}</span>
        </div>
        <LootName name={item.target_name} />
        <p className="text-[11px] opacity-80">
          {item.is_new
            ? "ショップで購入できるようになりました"
            : `所持済みのため +${item.credits_awarded.toLocaleString()} C に換金`}
        </p>
      </div>
      {item.is_new ? (
        <HighlightTag label="NEW" />
      ) : (
        <span className="shrink-0 text-sm font-bold">
          +{item.credits_awarded.toLocaleString()} C
        </span>
      )}
    </>
  );
}

/** 技術断片の戦利品の本文と右端の表示 */
function TechFragmentLootBody({ item }: { item: TechFragmentLootItem }) {
  return (
    <>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[10px] tracking-widest opacity-70">
          <span>{TECH_FRAGMENT_LABEL}</span>
          <span>
            Lv{item.level}/{item.max_level}
          </span>
        </div>
        <LootName name={item.target_name} />
        <p className="text-[11px] opacity-80">{techFragmentLootMessage(item)}</p>
      </div>
      {item.is_level_up ? (
        <HighlightTag label="LV UP" />
      ) : item.credits_awarded > 0 ? (
        <span className="shrink-0 text-sm font-bold">
          +{item.credits_awarded.toLocaleString()} C
        </span>
      ) : (
        <span className="shrink-0 text-sm font-bold">+1</span>
      )}
    </>
  );
}

function LootName({ name }: { name: string }) {
  return (
    <p className="text-sm sm:text-base font-bold text-white truncate" title={name}>
      {name}
    </p>
  );
}

function HighlightTag({ label }: { label: string }) {
  return (
    <span className="shrink-0 bg-[#00f0ff] text-black text-xs font-bold px-2 py-0.5 tracking-widest">
      {label}
    </span>
  );
}
