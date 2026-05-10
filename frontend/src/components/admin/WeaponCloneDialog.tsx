/* frontend/src/components/admin/WeaponCloneDialog.tsx */
"use client";

import { useState } from "react";
import { MasterWeaponEntry } from "@/types/battle";

interface WeaponCloneDialogProps {
  source: MasterWeaponEntry;
  onConfirm: (newId: string) => Promise<void>;
  onClose: () => void;
}

export default function WeaponCloneDialog({
  source,
  onConfirm,
  onClose,
}: WeaponCloneDialogProps) {
  const [newId, setNewId] = useState(`${source.id}_copy`);
  const [error, setError] = useState<string | null>(null);
  const [isCloning, setIsCloning] = useState(false);

  const SNAKE_CASE_RE = /^[a-z0-9_]+$/;

  async function handleConfirm() {
    if (!SNAKE_CASE_RE.test(newId)) {
      setError("IDはスネークケース英数字のみ（例: beam_rifle_copy）");
      return;
    }
    setError(null);
    setIsCloning(true);
    try {
      await onConfirm(newId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "クローン作成に失敗しました");
    } finally {
      setIsCloning(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-[#050505] border border-[#00ff41]/40 p-6 w-full max-w-sm font-mono text-[#00ff41]">
        <h2 className="text-base font-bold text-[#ffb000] mb-4">Clone &amp; Edit</h2>
        <p className="text-sm text-[#00ff41]/70 mb-4">
          <span className="text-[#ffb000]">{source.name}</span>{" "}
          をコピーして新規武器を作成します。新しい ID を入力してください。
        </p>
        <div className="mb-3">
          <label className="block text-xs text-[#ffb000]/80 mb-1">
            新しい ID (snake_case)
          </label>
          <input
            type="text"
            value={newId}
            onChange={(e) => setNewId(e.target.value)}
            className="w-full bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] px-3 py-2 text-sm focus:outline-none focus:border-[#00ff41]"
          />
          {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleConfirm}
            disabled={isCloning}
            className="flex-1 bg-[#00ff41]/10 border border-[#00ff41] text-[#00ff41] py-2 text-sm font-bold hover:bg-[#00ff41]/20 disabled:opacity-50"
          >
            {isCloning ? "作成中..." : "作成"}
          </button>
          <button
            onClick={onClose}
            className="flex-1 border border-[#00ff41]/30 text-[#00ff41]/60 py-2 text-sm hover:border-[#00ff41]/60"
          >
            キャンセル
          </button>
        </div>
      </div>
    </div>
  );
}
