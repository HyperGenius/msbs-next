/* admin-tool/src/app/ace-pilots/page.tsx */
"use client";

import { useState } from "react";
import { useAdminAcePilots } from "@/hooks/useAdminAcePilots";
import { AcePilot } from "@/types/admin";
import { Weapon } from "@/types/weapon";
import AcePilotTable from "@/components/admin/AcePilotTable";
import AcePilotEditForm, { AcePilotFormValues, toAcePilotPayload } from "@/components/admin/AcePilotEditForm";
import { SciFiPanel, SciFiHeading, SciFiButton } from "@/components/ui";

type Mode = "idle" | "edit" | "create";

interface Toast {
  message: string;
  type: "success" | "error";
}

export default function AdminAcePilotsPage() {
  const { acePilots, isLoading, isError, createAcePilot, updateAcePilot, deleteAcePilot } = useAdminAcePilots();

  const [selectedAce, setSelectedAce] = useState<AcePilot | null>(null);
  const [mode, setMode] = useState<Mode>("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);
  const [deleteConfirmAce, setDeleteConfirmAce] = useState<AcePilot | null>(null);

  function showToast(message: string, type: "success" | "error") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }

  function handleSelect(ace: AcePilot) {
    setSelectedAce(ace);
    setMode("edit");
  }

  function handleNew() {
    setSelectedAce(null);
    setMode("create");
  }

  async function handleSubmit(values: AcePilotFormValues, importedWeapons: Weapon[]) {
    setIsSubmitting(true);
    try {
      if (mode === "create") {
        await createAcePilot(toAcePilotPayload(values, null, importedWeapons));
        showToast(`${values.name} を新規追加しました`, "success");
        setMode("idle");
        setSelectedAce(null);
      } else if (mode === "edit" && selectedAce) {
        const updated = await updateAcePilot(selectedAce.id, toAcePilotPayload(values, selectedAce, importedWeapons));
        setSelectedAce(updated);
        showToast(`${values.name} を更新しました`, "success");
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : "エラーが発生しました", "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteConfirmAce) return;
    try {
      await deleteAcePilot(deleteConfirmAce.id);
      showToast(`${deleteConfirmAce.name} を削除しました`, "success");
      if (selectedAce?.id === deleteConfirmAce.id) {
        setSelectedAce(null);
        setMode("idle");
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : "削除に失敗しました", "error");
    } finally {
      setDeleteConfirmAce(null);
    }
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-[#050505] text-[#00ff41] p-8 font-mono">
        <SciFiPanel variant="secondary">
          <div className="p-6">
            <p className="text-[#ffb000] font-bold text-xl mb-2">ERROR: データ取得失敗</p>
            <p className="text-sm">
              ADMIN_API_KEY が正しく設定されているか、バックエンドが起動しているか確認してください。
            </p>
          </div>
        </SciFiPanel>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[#050505] text-[#00ff41] p-4 sm:p-6 font-mono">
      <div className="max-w-screen-xl mx-auto">
        {/* ヘッダー */}
        <div className="mb-6 border-b-2 border-[#ffb000]/30 pb-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <SciFiHeading level={2} variant="secondary" className="text-xl sm:text-2xl">
              ADMIN: ACE PILOTS
            </SciFiHeading>
            <p className="text-xs text-[#ffb000]/60 ml-0 sm:ml-5">
              エースパイロット マスターデータ管理（変更は次回マッチングから反映）
            </p>
          </div>
          <SciFiButton variant="secondary" size="sm" onClick={handleNew}>
            + 新規追加
          </SciFiButton>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 左カラム: エース一覧 */}
          <SciFiPanel variant="primary">
            <div className="p-4">
              <SciFiHeading level={3} className="mb-3 text-base">
                エース一覧
              </SciFiHeading>
              {isLoading ? (
                <p className="text-[#ffb000] animate-pulse py-8 text-center">LOADING...</p>
              ) : (
                <AcePilotTable
                  acePilots={acePilots ?? []}
                  selectedId={selectedAce?.id ?? null}
                  onSelect={handleSelect}
                  onDelete={setDeleteConfirmAce}
                />
              )}
            </div>
          </SciFiPanel>

          {/* 右カラム: 編集フォーム */}
          <div>
            {mode === "edit" || mode === "create" ? (
              <SciFiPanel variant="secondary">
                <div className="p-4">
                  <SciFiHeading level={3} className="mb-3 text-base">
                    {mode === "create" ? "新規エース追加" : `編集: ${selectedAce?.name}`}
                  </SciFiHeading>
                  {/* 対象が変わったらタブ状態ごとリセットするため key で再マウントする */}
                  <AcePilotEditForm
                    key={mode === "edit" ? selectedAce?.id : "new"}
                    initialData={mode === "edit" ? selectedAce : null}
                    lockId={mode === "edit"}
                    onSubmit={handleSubmit}
                    onCancel={() => setMode("idle")}
                    isSubmitting={isSubmitting}
                  />
                </div>
              </SciFiPanel>
            ) : (
              <SciFiPanel variant="primary">
                <div className="p-4 flex items-center justify-center h-48">
                  <p className="text-[#00ff41]/40 text-sm text-center">
                    エースを選択するか「新規追加」ボタンを押してください
                  </p>
                </div>
              </SciFiPanel>
            )}
          </div>
        </div>
      </div>

      {/* トースト通知 */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-sm border px-4 py-3 text-sm font-mono ${
            toast.type === "success"
              ? "bg-[#050505] border-[#00ff41]/60 text-[#00ff41]"
              : "bg-[#050505] border-red-500/60 text-red-400"
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* 削除確認ダイアログ */}
      {deleteConfirmAce && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-[#050505] border border-red-500/50 p-6 w-full max-w-sm font-mono text-[#00ff41]">
            <h2 className="text-base font-bold text-red-400 mb-3">削除確認</h2>
            <p className="text-sm text-[#00ff41]/80 mb-2">
              <span className="text-red-300 font-bold">{deleteConfirmAce.name}</span>（
              {deleteConfirmAce.pilot_name}）を削除しますか？ この操作は取り消せません。
            </p>
            <p className="text-xs text-[#00ff41]/50 mb-5">
              ※ 出撃済みのエース機は性格ベースの既定ステータス・スキルで動作するようになります
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleDeleteConfirm}
                className="flex-1 bg-red-900/30 border border-red-500/60 text-red-400 py-2 text-sm font-bold hover:bg-red-900/50"
              >
                削除する
              </button>
              <button
                onClick={() => setDeleteConfirmAce(null)}
                className="flex-1 border border-[#00ff41]/30 text-[#00ff41]/60 py-2 text-sm hover:border-[#00ff41]/60"
              >
                キャンセル
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
