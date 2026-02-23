/* frontend/src/app/garage/components/WeaponChangeModal.tsx */
"use client";

import { MobileSuit, WeaponListing, Pilot } from "@/types/battle";
import { SciFiButton, SciFiCard, SciFiHeading, SciFiPanel } from "@/components/ui";
import { calcWeaponDiff, diffColor, diffText } from "../utils";

interface WeaponChangeModalProps {
  selectedMs: MobileSuit;
  selectedWeaponSlot: number;
  weaponListings: WeaponListing[] | undefined;
  pilot: Pilot | undefined;
  previewWeaponId: string | null;
  onSetPreviewWeaponId: (id: string | null) => void;
  onEquipWeapon: (weaponId: string) => void;
  onClose: () => void;
}

export default function WeaponChangeModal({
  selectedMs,
  selectedWeaponSlot,
  weaponListings,
  pilot,
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
      pilot.inventory[wl.id] > 0
  );

  const hasOwnedWeapons =
    pilot?.inventory &&
    weaponListings?.some(
      (w) => pilot.inventory?.[w.id] && pilot.inventory[w.id] > 0
    );

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
      <SciFiPanel variant="accent" chiseled={true}>
        <div className="p-8 max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
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
            所持している武器から選択してください
          </p>

          {/* Preview */}
          {previewListing && (() => {
            const diff = calcWeaponDiff(currentWeapon, previewListing.weapon);
            return (
              <div className="mb-4 p-3 bg-gray-900 rounded border border-green-700">
                <p className="text-xs font-bold text-green-400 mb-2">
                  ▶ 装備変更プレビュー: {previewListing.weapon.name}
                </p>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <span className="text-gray-400">威力:</span>
                    <span className="ml-1 font-bold">{previewListing.weapon.power}</span>
                    <span className={`ml-1 ${diffColor(diff.power)}`}>
                      ({diffText(diff.power)})
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">射程:</span>
                    <span className="ml-1 font-bold">{previewListing.weapon.range}m</span>
                    <span className={`ml-1 ${diffColor(diff.range)}`}>
                      ({diffText(diff.range)})
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">命中:</span>
                    <span className="ml-1 font-bold">{previewListing.weapon.accuracy}%</span>
                    <span className={`ml-1 ${diffColor(diff.accuracy)}`}>
                      ({diffText(diff.accuracy)})
                    </span>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Weapon list */}
          <div className="space-y-3 mb-6">
            {ownedListings?.map((weaponListing) => {
              const weapon = weaponListing.weapon;
              const diff = calcWeaponDiff(currentWeapon, weapon);
              return (
                <div
                  key={weaponListing.id}
                  onMouseEnter={() => onSetPreviewWeaponId(weaponListing.id)}
                  onMouseLeave={() => onSetPreviewWeaponId(null)}
                >
                  <SciFiCard
                    variant="accent"
                    className="cursor-pointer hover:border-green-400 transition-colors"
                    onClick={() => onEquipWeapon(weaponListing.id)}
                  >
                    <div className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <h4 className="font-bold text-green-300">
                            {weapon.name}
                          </h4>
                          <p className="text-xs text-green-600">
                            所持数: {pilot?.inventory?.[weaponListing.id] || 0}
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
                          <span className="text-gray-400">威力:</span>
                          <span className="ml-1 font-bold text-green-400">
                            {weapon.power}
                          </span>
                          {currentWeapon && (
                            <span className={`ml-1 text-xs ${diffColor(diff.power)}`}>
                              ({diffText(diff.power)})
                            </span>
                          )}
                        </div>
                        <div>
                          <span className="text-gray-400">射程:</span>
                          <span className="ml-1 font-bold text-green-400">
                            {weapon.range}m
                          </span>
                          {currentWeapon && (
                            <span className={`ml-1 text-xs ${diffColor(diff.range)}`}>
                              ({diffText(diff.range)})
                            </span>
                          )}
                        </div>
                        <div>
                          <span className="text-gray-400">命中:</span>
                          <span className="ml-1 font-bold text-green-400">
                            {weapon.accuracy}%
                          </span>
                          {currentWeapon && (
                            <span className={`ml-1 text-xs ${diffColor(diff.accuracy)}`}>
                              ({diffText(diff.accuracy)})
                            </span>
                          )}
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
          </div>
        </div>
      </SciFiPanel>
    </div>
  );
}
