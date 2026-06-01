/** Sticky ヘッダー: クレジット残高・タブ・アフォーダビリティフィルターを統合表示する */
"use client";

import { SciFiButton } from "@/components/ui";

type TabType = "mobile_suits" | "weapons";
type FilterType = "all" | "affordable";

interface ShopCreditHeaderProps {
  credits: number;
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  filter: FilterType;
  onFilterChange: (filter: FilterType) => void;
}

export default function ShopCreditHeader({
  credits,
  activeTab,
  onTabChange,
  filter,
  onFilterChange,
}: ShopCreditHeaderProps) {
  return (
    <div className="sticky top-0 z-40 bg-[#0a0a0a] border-b border-[#00ff41]/30 pt-3 pb-3 px-4 sm:px-6 md:px-8">
      {/* クレジット残高 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#00ff41]/50 font-mono tracking-widest">CREDITS</span>
          <span className="text-xl font-bold text-[#ffb000] font-mono">
            {credits.toLocaleString()} C
          </span>
        </div>
        <span className="text-xs text-[#00ff41]/40 font-mono">
          {activeTab === "mobile_suits" ? "MOBILE SUIT SHOP" : "WEAPON SHOP"}
        </span>
      </div>

      {/* タブ */}
      <div className="flex gap-2 mb-2">
        <SciFiButton
          variant={activeTab === "mobile_suits" ? "secondary" : "primary"}
          size="sm"
          onClick={() => onTabChange("mobile_suits")}
          className="flex-1 sm:flex-none"
        >
          Mobile Suits
        </SciFiButton>
        <SciFiButton
          variant={activeTab === "weapons" ? "secondary" : "primary"}
          size="sm"
          onClick={() => onTabChange("weapons")}
          className="flex-1 sm:flex-none"
        >
          Weapons
        </SciFiButton>
      </div>

      {/* フィルターチップ */}
      <div className="flex gap-2">
        <button
          onClick={() => onFilterChange("all")}
          className={`px-3 py-1 text-xs font-mono border transition-colors ${
            filter === "all"
              ? "border-[#00ff41] text-[#00ff41] bg-[#00ff41]/10"
              : "border-[#00ff41]/30 text-[#00ff41]/50 hover:border-[#00ff41]/60 hover:text-[#00ff41]/70"
          }`}
        >
          全て
        </button>
        <button
          onClick={() => onFilterChange("affordable")}
          className={`px-3 py-1 text-xs font-mono border transition-colors ${
            filter === "affordable"
              ? "border-[#ffb000] text-[#ffb000] bg-[#ffb000]/10"
              : "border-[#00ff41]/30 text-[#00ff41]/50 hover:border-[#ffb000]/60 hover:text-[#ffb000]/70"
          }`}
        >
          購入可能のみ
        </button>
      </div>
    </div>
  );
}
