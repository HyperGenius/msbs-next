/* frontend/src/app/garage/components/WeaponChangeModal.tsx */
"use client";

import { MobileSuit, Weapon, WeaponListing, Pilot } from "@/types/battle";
import { SciFiButton, SciFiCard, SciFiHeading, SciFiPanel } from "@/components/ui";
import { getRankColor, getWeaponRank } from "@/utils/rankUtils";
import { WEAPON_LABELS } from "@/utils/displayUtils";

interface WeaponChangeModalProps {
  selectedMs: MobileSuit;
  selectedWeaponSlot: number;
  weaponListings: WeaponListing[] | undefined;
  pilot: Pilot | undefined;
  ownedMobileSuits: MobileSuit[];
  previewWeaponId: string | null;
  onSetPreviewWeaponId: (id: string | null) => void;
  onEquipWeapon: (weaponId: string) => void;
  onClose: () => void;
}

const RANK_ORDER = ["S", "A", "B", "C", "D", "E"];

function resolveRank(weapon: Weapon, field: "power" | "range" | "accuracy"): string {
  if (field === "power") return weapon.power_rank ?? getWeaponRank("weapon_power", weapon.power);
  if (field === "range") return weapon.range_rank ?? getWeaponRank("weapon_range", weapon.range);
  return weapon.accuracy_rank ?? getWeaponRank("weapon_accuracy", weapon.accuracy);
}

/** ランク比較: 新ランクが上位なら正、下位なら負、同じなら0 */
function rankCompare(currentRank: string, newRank: string): number {
  return RANK_ORDER.indexOf(currentRank) - RANK_ORDER.indexOf(newRank);
}

interface RankDiffBadgeProps {
  currentRank: string | undefined;
  newRank: string;
}

function RankDiffBadge({ currentRank, newRank }: RankDiffBadgeProps) {
  const diff = currentRank ? rankCompare(currentRank, newRank) : 0;
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`font-bold ${getRankColor(newRank)}`}>{newRank}</span>
      {currentRank && diff !== 0 && (
        <span className={`text-xs ${diff > 0 ? "text-green-400" : "text-red-400"}`}>
          ({diff > 0 ? "↑" : "↓"}{currentRank}→{newRank})
        </span>
      )}
    </span>
  );
}

export default function WeaponChangeModal({
  selectedMs,
  selectedWeaponSlot,
  weaponListings,
  pilot,
  ownedMobileSuits,
  previewWeaponId,
  onSetPreviewWeaponId,
  onEquipWeapon,
  onClose,
}: WeaponChangeModalProps) {
  const currentWeapon = selectedMs.weapons?.[selectedWeaponSlot];
  const previewListing = previewWeaponId
    ? weaponListings?.find((w) => w.id === previewWeaponId)
    : null;

  const ownedListings = weaponListings?.filter(
    (wl) =>
      pilot?.inventory &&
      pilot.inventory[wl.id] &&
      pilot.inventory[wl.id] > 0 &&
      wl.id !== currentWeapon?.id
  );

  const hasOwnedWeapons =
    pilot?.inventory &&
    weaponListings?.some(
      (w) => pilot.inventory?.[w.id] && pilot.inventory[w.id] > 0
    );

  /**
   * 全機体の装備から weapon_id の装備数を算出する。
   * ただし装備対象スロットに既に同じ武器が入っている場合はカウントから除外する
   * （付け替えのため、そのスロットは "空き" 扱いにする）。
   */
  const calcAvailableCount = (weaponId: string): number => {
    const totalOwned = pilot?.inventory?.[weaponId] || 0;
    const totalEquipped = ownedMobileSuits.reduce((sum, ms) => {
      return sum + (ms.weapons || []).filter((w) => w.id === weaponId).length;
    }, 0);
    // 対象スロットに同じ武器が既にある場合は付け替えなので 1 戻す
    const alreadyInSlot =
      selectedMs.weapons?.[selectedWeaponSlot]?.id === weaponId ? 1 : 0;
    return totalOwned - totalEquipped + alreadyInSlot;
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
      <SciFiPanel variant="accent" chiseled={true}>
        <div className="p-8 max-w-2xl mx-4 h-[80vh] flex flex-col">
          <SciFiHeading level={3} className="mb-1" variant="accent">
            武器変更
          </SciFiHeading>
          <p className="mb-1 text-xs text-green-600">
            スロット:{" "}
            {selectedWeaponSlot === 0
              ? "【MAIN】メイン武器"
              : "【SUB】サブ武器"}
          </p>
          <p className="mb-4 text-sm text-green-400">
            武器を選択してプレビューを確認後、装備するボタンを押してください
          </p>

          {/* Preview — fixed height area to prevent layout shift */}
          <div className="mb-4 p-3 bg-gray-900 rounded border border-green-700 min-h-[80px] flex flex-col justify-center">
            {previewListing ? (() => {
              const pw = previewListing.weapon;
              return (
                <>
                  <p className="text-xs font-bold text-green-400 mb-2">
                    ▶ 装備変更プレビュー: {pw.name}
                  </p>
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <span className="text-gray-400">{WEAPON_LABELS.power}:</span>
                      <span className="ml-1">
                        <RankDiffBadge
                          currentRank={currentWeapon ? resolveRank(currentWeapon, "power") : undefined}
                          newRank={resolveRank(pw, "power")}
                        />
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400">{WEAPON_LABELS.range}:</span>
                      <span className="ml-1">
                        <RankDiffBadge
                          currentRank={currentWeapon ? resolveRank(currentWeapon, "range") : undefined}
                          newRank={resolveRank(pw, "range")}
                        />
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400">{WEAPON_LABELS.accuracy}:</span>
                      <span className="ml-1">
                        <RankDiffBadge
                          currentRank={currentWeapon ? resolveRank(currentWeapon, "accuracy") : undefined}
                          newRank={resolveRank(pw, "accuracy")}
                        />
                      </span>
                    </div>
                  </div>
                </>
              );
            })() : (
              <p className="text-xs text-gray-500 text-center">
                武器カードをタップして選択してください
              </p>
            )}
          </div>

          {/* Weapon list */}
          <div className="space-y-3 mb-6 overflow-y-auto flex-1">
            {ownedListings?.map((weaponListing) => {
              const weapon = weaponListing.weapon;
              const totalCount = pilot?.inventory?.[weaponListing.id] || 0;
              const availableCount = calcAvailableCount(weaponListing.id);
              const isDisabled = availableCount <= 0;
              const isSelected = previewWeaponId === weaponListing.id;
              return (
                <div key={weaponListing.id}>
                  <SciFiCard
                    variant="accent"
                    className={
                      isDisabled
                        ? "opacity-40 cursor-not-allowed"
                        : isSelected
                        ? "cursor-pointer border-green-400 ring-1 ring-green-400 transition-colors"
                        : "cursor-pointer hover:border-green-400 transition-colors"
                    }
                    onClick={() =>
                      !isDisabled &&
                      onSetPreviewWeaponId(isSelected ? null : weaponListing.id)
                    }
                  >
                    <div className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h4 className="font-bold text-green-300">
                            {weapon.name}
                          </h4>
                          <p className="text-xs text-green-600">
                            利用可能: {availableCount} / 所持: {totalCount}
                          </p>
                        </div>
                        <span
                          className={`px-2 py-1 text-xs font-bold rounded ${
                            weapon.type === "BEAM"
                              ? "bg-blue-500/20 text-blue-400"
                              : "bg-yellow-500/20 text-yellow-400"
                          }`}
                        >
                          {weapon.type || "PHYSICAL"}
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <div>
                          <span className="text-gray-400">{WEAPON_LABELS.power}:</span>
                          <span className="ml-1">
                            <RankDiffBadge
                              currentRank={currentWeapon ? resolveRank(currentWeapon, "power") : undefined}
                              newRank={resolveRank(weapon, "power")}
                            />
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400">{WEAPON_LABELS.range}:</span>
                          <span className="ml-1">
                            <RankDiffBadge
                              currentRank={currentWeapon ? resolveRank(currentWeapon, "range") : undefined}
                              newRank={resolveRank(weapon, "range")}
                            />
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400">{WEAPON_LABELS.accuracy}:</span>
                          <span className="ml-1">
                            <RankDiffBadge
                              currentRank={currentWeapon ? resolveRank(currentWeapon, "accuracy") : undefined}
                              newRank={resolveRank(weapon, "accuracy")}
                            />
                          </span>
                        </div>
                      </div>
                    </div>
                  </SciFiCard>
                </div>
              );
            })}

            {!hasOwnedWeapons && (
              <div className="text-center py-8 text-gray-400">
                <p>所持している武器がありません</p>
                <p className="text-sm mt-2">
                  ショップで武器を購入してください
                </p>
              </div>
            )}
          </div>

          <div className="flex gap-4">
            <SciFiButton
              onClick={onClose}
              variant="danger"
              size="md"
              className="flex-1"
            >
              閉じる
            </SciFiButton>
            <SciFiButton
              onClick={() => {
                if (previewWeaponId) {
                  onEquipWeapon(previewWeaponId);
                }
              }}
              variant="accent"
              size="md"
              className="flex-1"
              disabled={!previewWeaponId}
            >
              装備する
            </SciFiButton>
          </div>
        </div>
      </SciFiPanel>
    </div>
  );
}

