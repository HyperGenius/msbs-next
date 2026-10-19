/* frontend/src/app/garage/components/WeaponEquipPanel.tsx */
"use client";

import { useMemo, useState } from "react";
import { PlayerWeapon } from "@/types/battle";
import { EnrichedMobileSuit } from "@/utils/rankUtils";
import { SciFiButton, SciFiSelect } from "@/components/ui";
import { usePlayerWeapons } from "@/hooks/usePlayerWeapons";
import { getWeaponSlots, getWeaponSlotLabel } from "../constants";
import { resolveWeaponSpec } from "../weaponUpgrade";

interface WeaponEquipPanelProps {
  playerWeapon: PlayerWeapon;
  mobileSuits: EnrichedMobileSuit[] | undefined;
  isBusy: boolean;
  /** 装備に成功したら true を返す */
  onEquip: (playerWeaponId: string, msId: string, slotIndex: number) => Promise<boolean>;
  onNavigateToEquippedMs: (msId: string) => void;
}

/**
 * 武器改造モーダルの「装備」タブ。
 * 未装備の武器は装備先の機体とスロットを選んで装備する。装備中の武器は装備先へ移動する導線を出す。
 */
export default function WeaponEquipPanel({
  playerWeapon,
  mobileSuits,
  isBusy,
  onEquip,
  onNavigateToEquippedMs,
}: WeaponEquipPanelProps) {
  const equippedMs = playerWeapon.equipped_ms_id
    ? mobileSuits?.find((ms) => ms.id === playerWeapon.equipped_ms_id)
    : undefined;

  if (playerWeapon.equipped_ms_id !== null) {
    return (
      <>
        <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 text-sm">
          {equippedMs ? (
            <p className="text-[#00ff41]/80">
              {equippedMs.name}の
              {getWeaponSlotLabel(playerWeapon.equipped_slot ?? 0)}に装備中です。
              付け替えは機体の LOADOUT タブから行えます。
            </p>
          ) : (
            <p className="font-bold text-[#ffb000]">装備先: 不明な機体</p>
          )}
        </div>
        {equippedMs && (
          <div className="shrink-0 p-4 sm:px-6 border-t border-[#00ff41]/20">
            <button
              type="button"
              onClick={() => onNavigateToEquippedMs(equippedMs.id)}
              className="w-full min-h-11 border border-[#00ff41] text-[#00ff41] bg-transparent hover:bg-[#00ff41] hover:text-black active:bg-[#00ff41] active:text-black transition-colors font-bold font-mono text-sm px-4 py-2.5"
            >
              → {equippedMs.name}へ移動
            </button>
          </div>
        )}
      </>
    );
  }

  return (
    <UnequippedWeaponForm
      playerWeapon={playerWeapon}
      mobileSuits={mobileSuits}
      isBusy={isBusy}
      onEquip={onEquip}
    />
  );
}

interface UnequippedWeaponFormProps {
  playerWeapon: PlayerWeapon;
  mobileSuits: EnrichedMobileSuit[] | undefined;
  isBusy: boolean;
  onEquip: (playerWeaponId: string, msId: string, slotIndex: number) => Promise<boolean>;
}

/** 未装備の武器の装備先（機体・スロット）を選ぶフォーム。 */
function UnequippedWeaponForm({
  playerWeapon,
  mobileSuits,
  isBusy,
  onEquip,
}: UnequippedWeaponFormProps) {
  const spec = resolveWeaponSpec(playerWeapon);
  const [selectedMsId, setSelectedMsId] = useState<string>("");
  const [selectedSlot, setSelectedSlot] = useState<number>(0);

  // スロットに入っている武器の名前を出すため、装備済みも含めた全件を引く。
  // 同じ URL の SWR キャッシュを Garage と共有するので、追加のリクエストは発生しない。
  const { playerWeapons } = usePlayerWeapons();

  const selectedMs = mobileSuits?.find((ms) => ms.id === selectedMsId);

  // 装備状態は PlayerWeapon を正とする。機体の初期装備は PlayerWeapon を持たないため、
  // PlayerWeapon が無いスロットだけ MobileSuit.weapons の名前で補う。
  const occupantBySlot = useMemo(() => {
    const map = new Map<number, string>();
    if (!selectedMs) return map;
    selectedMs.weapons?.forEach((w, index) => map.set(index, w.name));
    playerWeapons?.forEach((pw) => {
      if (pw.equipped_ms_id === selectedMs.id && pw.equipped_slot !== null) {
        map.set(pw.equipped_slot, resolveWeaponSpec(pw).name);
      }
    });
    return map;
  }, [playerWeapons, selectedMs]);

  // バックエンドは手前のスロットを飛ばした装備を拒否する。
  // 判定には MobileSuit.weapons の長さを使う（バックエンドの検証と同じ基準）。
  const equippableSlots = selectedMs
    ? getWeaponSlots(selectedMs.weapon_slot_count).filter(
        (slot) => slot.index <= (selectedMs.weapons?.length ?? 0)
      )
    : [];

  const requiredBeamLv =
    spec.type === "BEAM" ? (spec.required_beam_generator_lv ?? 0) : 0;
  const lacksBeamGenerator =
    !!selectedMs && requiredBeamLv > (selectedMs.beam_generator_lv ?? 0);

  const occupantName = occupantBySlot.get(selectedSlot);

  const handleSelectMs = (msId: string) => {
    setSelectedMsId(msId);
    const ms = mobileSuits?.find((m) => m.id === msId);
    if (!ms) return;
    // 空きスロットがあれば初期選択にする。意図しない入れ替えを避けるため。
    const firstEmptySlot = ms.weapons?.length ?? 0;
    const slotCount = getWeaponSlots(ms.weapon_slot_count).length;
    setSelectedSlot(firstEmptySlot < slotCount ? firstEmptySlot : 0);
  };

  return (
    <>
      <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 space-y-3">
        <SciFiSelect
          label="装備先の機体"
          value={selectedMsId}
          onChange={(e) => handleSelectMs(e.target.value)}
          className="min-h-11"
          options={[
            { value: "", label: "機体を選択" },
            ...(mobileSuits?.map((ms) => ({ value: ms.id, label: ms.name })) ?? []),
          ]}
        />

        {selectedMs && (
          <SciFiSelect
            label="スロット"
            value={selectedSlot}
            onChange={(e) => setSelectedSlot(Number(e.target.value))}
            className="min-h-11"
            options={equippableSlots.map((slot) => {
              const occupant = occupantBySlot.get(slot.index);
              return {
                value: slot.index,
                label: occupant ? `${slot.labelJa}（${occupant}）` : `${slot.labelJa}（空き）`,
              };
            })}
          />
        )}

        {lacksBeamGenerator && (
          <p className="text-xs text-red-400">
            この武器の装備にはビームジェネレータLv{requiredBeamLv}が必要です（
            {selectedMs?.name}はLv{selectedMs?.beam_generator_lv ?? 0}）
          </p>
        )}
        {!lacksBeamGenerator && occupantName && (
          <p className="text-xs text-[#ffb000]">
            装備すると、このスロットの {occupantName} は外れます。
          </p>
        )}
      </div>

      <div className="shrink-0 p-4 sm:px-6 border-t border-[#00ff41]/20">
        <SciFiButton
          variant="accent"
          className="w-full min-h-11"
          disabled={!selectedMsId || lacksBeamGenerator || isBusy}
          onClick={() => onEquip(playerWeapon.id, selectedMsId, selectedSlot)}
        >
          {isBusy ? "装備中..." : "装備する"}
        </SciFiButton>
      </div>
    </>
  );
}
