/* admin-tool/src/components/admin/MasterMobileSuitSelect.tsx */
"use client";

import { useState } from "react";
import { useAdminMobileSuits } from "@/hooks/useAdminMobileSuits";
import { MasterMobileSuit } from "@/types/admin";
import { inputCls } from "@/components/admin/MobileSuitSpecFields";

export function masterMobileSuitLabel(ms: MasterMobileSuit): string {
  if (!ms.name_ja) return ms.name;
  return ms.model_number ? `${ms.name_ja} (${ms.model_number})` : ms.name_ja;
}

interface MasterMobileSuitSelectProps {
  buttonLabel: string;
  onApply: (master: MasterMobileSuit) => void | Promise<void>;
  disabled?: boolean;
}

/** 機体マスターをプルダウンで選び、ボタン押下で呼び出し元へ渡す */
export default function MasterMobileSuitSelect({ buttonLabel, onApply, disabled = false }: MasterMobileSuitSelectProps) {
  const { mobileSuits, isLoading, isError } = useAdminMobileSuits();
  const [selectedId, setSelectedId] = useState("");
  const selected = mobileSuits?.find((ms) => ms.id === selectedId);

  return (
    <div className="flex gap-2">
      <select
        value={selectedId}
        onChange={(e) => setSelectedId(e.target.value)}
        disabled={isLoading || !!isError}
        className={inputCls}
      >
        <option value="">
          {isLoading ? "読み込み中..." : isError ? "機体マスターを取得できません" : "機体マスターを選択"}
        </option>
        {(mobileSuits ?? []).map((ms) => (
          <option key={ms.id} value={ms.id}>
            {masterMobileSuitLabel(ms)}
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
