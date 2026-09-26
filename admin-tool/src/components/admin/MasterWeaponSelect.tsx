/* admin-tool/src/components/admin/MasterWeaponSelect.tsx */
"use client";

import { useState } from "react";
import { useAdminWeapons } from "@/hooks/useAdminWeapons";
import { MasterWeapon } from "@/types/admin";
import { inputCls } from "@/components/admin/MobileSuitSpecFields";

export function masterWeaponLabel(w: MasterWeapon): string {
  return `${w.name} (${w.id})`;
}

interface MasterWeaponSelectProps {
  buttonLabel: string;
  onApply: (master: MasterWeapon) => void;
  disabled?: boolean;
}

/** 武器マスターをプルダウンで選び、ボタン押下で呼び出し元へ渡す */
export default function MasterWeaponSelect({ buttonLabel, onApply, disabled = false }: MasterWeaponSelectProps) {
  const { weapons, isLoading, isError } = useAdminWeapons();
  const [selectedId, setSelectedId] = useState("");
  const selected = weapons?.find((w) => w.id === selectedId);

  return (
    <div className="flex gap-2">
      <select
        value={selectedId}
        onChange={(e) => setSelectedId(e.target.value)}
        disabled={isLoading || !!isError}
        className={inputCls}
      >
        <option value="">
          {isLoading ? "読み込み中..." : isError ? "武器マスターを取得できません" : "武器マスターを選択"}
        </option>
        {(weapons ?? []).map((w) => (
          <option key={w.id} value={w.id}>
            {masterWeaponLabel(w)}
          </option>
        ))}
      </select>
      <button
        type="button"
        disabled={!selected || disabled}
        onClick={() => selected && onApply(selected)}
        className="shrink-0 text-xs text-[#00ff41] border border-[#00ff41]/40 px-3 hover:border-[#00ff41] disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {buttonLabel}
      </button>
    </div>
  );
}
