/* frontend/src/app/garage/components/WeaponUpgradeModal.tsx */
"use client";

import { useState } from "react";
import { PlayerWeapon, Pilot } from "@/types/battle";
import { EnrichedMobileSuit } from "@/utils/rankUtils";
import SciFiModal from "@/components/ui/SciFiModal";
import { SciFiHeading } from "@/components/ui";
import { resolveWeaponSpec } from "../weaponUpgrade";
import AimDistributionEditor from "./AimDistributionEditor";
import WeaponEquipPanel from "./WeaponEquipPanel";
import WeaponResourceBadges from "./WeaponResourceBadges";
import WeaponUpgradePanel from "./WeaponUpgradePanel";

export type WeaponModalTab = "UPGRADE" | "AIM" | "EQUIP";

const TABS: { key: WeaponModalTab; label: string }[] = [
  { key: "UPGRADE", label: "改造" },
  { key: "AIM", label: "狙う部位配分" },
  { key: "EQUIP", label: "装備" },
];

interface WeaponUpgradeModalProps {
  playerWeapon: PlayerWeapon;
  pilot: Pilot | undefined;
  mobileSuits: EnrichedMobileSuit[] | undefined;
  isBusy: boolean;
  initialTab: WeaponModalTab;
  onClose: () => void;
  /** 改造・部位配分の更新成功時に呼ばれる（更新後の PlayerWeapon を渡す） */
  onUpgraded: (updated: PlayerWeapon) => void;
  /** 装備に成功したら true を返す */
  onEquip: (playerWeaponId: string, msId: string, slotIndex: number) => Promise<boolean>;
  onNavigateToEquippedMs: (msId: string) => void;
}

/** 所持武器 1 件の改造・狙う部位配分・装備をタブで切り替えて操作するモーダル。 */
export default function WeaponUpgradeModal({
  playerWeapon,
  pilot,
  mobileSuits,
  isBusy,
  initialTab,
  onClose,
  onUpgraded,
  onEquip,
  onNavigateToEquippedMs,
}: WeaponUpgradeModalProps) {
  const [activeTab, setActiveTab] = useState<WeaponModalTab>(initialTab);
  const spec = resolveWeaponSpec(playerWeapon);

  // 非表示のタブもアンマウントせず hidden で隠す。
  // 確定前の改造ステップや部位配分の入力を、タブを切り替えても残すため。
  const panelClass = (tab: WeaponModalTab) =>
    activeTab === tab ? "flex flex-col flex-1 min-h-0" : "hidden";

  return (
    <SciFiModal
      isOpen
      onClose={onClose}
      variant="primary"
      maxWidthClass="max-w-lg"
      fixedHeightClass="h-[min(85dvh,40rem)]"
    >
      <div className="shrink-0 px-4 pt-3 sm:px-6 sm:pt-6 border-b border-[#00ff41]/30">
        <div className="flex justify-between items-start gap-3">
          <SciFiHeading level={3} className="text-base sm:text-xl break-words min-w-0">
            {spec.name}
          </SciFiHeading>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 min-h-11 -mt-2 -mr-2 px-2 text-gray-400 hover:text-[#00ff41] transition-colors font-mono text-sm"
            aria-label="閉じる"
          >
            ✕ CLOSE
          </button>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span
            className={`px-2 py-0.5 text-xs font-bold rounded ${
              spec.type === "BEAM"
                ? "bg-blue-500/20 text-blue-400"
                : "bg-yellow-500/20 text-yellow-400"
            }`}
          >
            {spec.type || "PHYSICAL"}
          </span>
          <WeaponResourceBadges spec={spec} />
        </div>

        <div role="tablist" className="flex gap-1 mt-2 sm:mt-3 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`min-h-11 px-4 text-xs sm:text-sm font-bold font-mono tracking-wider transition-all whitespace-nowrap ${
                activeTab === tab.key
                  ? "bg-[#00ff41]/20 text-[#00ff41] border-b-2 border-[#00ff41]"
                  : "text-[#00ff41]/40 hover:text-[#00ff41]/70 hover:bg-[#00ff41]/5"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div role="tabpanel" className={panelClass("UPGRADE")}>
        <WeaponUpgradePanel
          playerWeapon={playerWeapon}
          pilot={pilot}
          onUpgraded={onUpgraded}
        />
      </div>
      <div role="tabpanel" className={panelClass("AIM")}>
        <AimDistributionEditor playerWeapon={playerWeapon} onUpdated={onUpgraded} />
      </div>
      <div role="tabpanel" className={panelClass("EQUIP")}>
        <WeaponEquipPanel
          playerWeapon={playerWeapon}
          mobileSuits={mobileSuits}
          isBusy={isBusy}
          onEquip={onEquip}
          onNavigateToEquippedMs={onNavigateToEquippedMs}
        />
      </div>
    </SciFiModal>
  );
}
