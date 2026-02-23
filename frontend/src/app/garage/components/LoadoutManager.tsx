/* frontend/src/app/garage/components/LoadoutManager.tsx */
"use client";

import { MobileSuit } from "@/types/battle";
import { WEAPON_SLOTS } from "../constants";
import { SciFiButton } from "@/components/ui";

interface LoadoutManagerProps {
  selectedMs: MobileSuit;
  onOpenWeaponModal: (slotIndex: number) => void;
}

export default function LoadoutManager({
  selectedMs,
  onOpenWeaponModal,
}: LoadoutManagerProps) {
  return (
    <div className="p-3 bg-gray-900 rounded border border-green-800">
      <h4 className="text-sm font-bold mb-3 text-green-500">
        装備換装 (Loadout)
      </h4>
      <div className="space-y-3">
        {WEAPON_SLOTS.map((slot) => {
          const equippedWeapon = selectedMs.weapons?.[slot.index];
          return (
            <div key={slot.index} className="p-2 bg-gray-800 rounded">
              <div className="flex justify-between items-center mb-2">
                <div>
                  <span className="text-xs font-bold text-green-400 uppercase">
                    [{slot.index === 0 ? "MAIN" : "SUB"}]
                  </span>
                  <span className="ml-2 text-xs text-gray-400">
                    {slot.labelJa}
                  </span>
                </div>
                <SciFiButton
                  variant="primary"
                  size="sm"
                  onClick={() => onOpenWeaponModal(slot.index)}
                >
                  変更
                </SciFiButton>
              </div>
              {equippedWeapon ? (
                <div className="text-xs space-y-1">
                  <div className="font-bold text-green-300">
                    {equippedWeapon.name}
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <span
                        className={`px-1 py-0.5 text-xs font-bold rounded ${
                          equippedWeapon.type === "BEAM"
                            ? "bg-blue-500/20 text-blue-400"
                            : "bg-yellow-500/20 text-yellow-400"
                        }`}
                      >
                        {equippedWeapon.type || "PHYSICAL"}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400">威力:</span>
                      <span className="ml-1 font-bold">{equippedWeapon.power}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">射程:</span>
                      <span className="ml-1 font-bold">{equippedWeapon.range}m</span>
                    </div>
                    <div>
                      <span className="text-gray-400">命中:</span>
                      <span className="ml-1 font-bold">{equippedWeapon.accuracy}%</span>
                    </div>
                    <div>
                      <span className="text-gray-400">最適:</span>
                      <span className="ml-1 font-bold text-green-400">
                        {equippedWeapon.optimal_range || 300}m
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-400">弾数:</span>
                      <span className="ml-1 font-bold text-orange-400">
                        {equippedWeapon.max_ammo != null
                          ? equippedWeapon.max_ammo
                          : "∞"}
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-xs text-gray-500 py-2 text-center">
                  — 未装備 —
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
