"use client";

import { useState } from "react";
import { useAdminTechnologies } from "@/hooks/useAdminTechnologies";
import { MasterTechnology } from "@/types/admin";
import { inputCls } from "@/components/admin/MobileSuitSpecFields";

interface MasterTechnologySelectProps {
  buttonLabel: string;
  onApply: (master: MasterTechnology) => void;
  disabled?: boolean;
}

/** 技術マスターをプルダウンで選び、ボタン押下で呼び出し元へ渡す */
export default function MasterTechnologySelect({
  buttonLabel,
  onApply,
  disabled = false,
}: MasterTechnologySelectProps) {
  const { technologies, isLoading, isError } = useAdminTechnologies();
  const [selectedId, setSelectedId] = useState("");
  const selected = technologies?.find((t) => t.id === selectedId);

  return (
    <div className="flex gap-2">
      <select
        value={selectedId}
        onChange={(e) => setSelectedId(e.target.value)}
        disabled={isLoading || !!isError}
        className={inputCls}
      >
        <option value="">
          {isLoading ? "読み込み中..." : isError ? "技術マスターを取得できません" : "技術マスターを選択"}
        </option>
        {(technologies ?? []).map((t) => (
          <option key={t.id} value={t.id}>
            {t.name} ({t.id})
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
