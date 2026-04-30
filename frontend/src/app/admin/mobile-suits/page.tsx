/* frontend/src/app/admin/mobile-suits/page.tsx */
"use client";

import { useState } from "react";
import { useAdminMobileSuits } from "@/hooks/useAdminMobileSuits";
import { MasterMobileSuit, MasterMobileSuitCreate } from "@/types/battle";
import MobileSuitTable from "@/components/admin/MobileSuitTable";
import MobileSuitEditForm, { MobileSuitFormValues } from "@/components/admin/MobileSuitEditForm";
import MobileSuitRadarChart from "@/components/admin/MobileSuitRadarChart";
import CloneDialog from "@/components/admin/CloneDialog";
import { SciFiPanel, SciFiHeading, SciFiButton } from "@/components/ui";

type Mode = "idle" | "edit" | "create";

interface Toast {
  message: string;
  type: "success" | "error";
}

export default function AdminMobileSuitsPage() {
  const { mobileSuits, isLoading, isError, createMobileSuit, updateMobileSuit, deleteMobileSuit } =
    useAdminMobileSuits();

  const [selectedMs, setSelectedMs] = useState<MasterMobileSuit | null>(null);
  const [mode, setMode] = useState<Mode>("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);
  const [cloneSource, setCloneSource] = useState<MasterMobileSuit | null>(null);
  const [deleteConfirmMs, setDeleteConfirmMs] = useState<MasterMobileSuit | null>(null);

  function showToast(message: string, type: "success" | "error") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }

  function handleSelectMs(ms: MasterMobileSuit) {
    setSelectedMs(ms);
    setMode("edit");
  }

  function handleNewMs() {
    setSelectedMs(null);
    setMode("create");
  }

  function handleCancel() {
    setMode("idle");
  }

  async function handleSubmit(values: MobileSuitFormValues) {
    setIsSubmitting(true);
    try {
      if (mode === "create") {
        await createMobileSuit(values as MasterMobileSuitCreate);
        showToast(`${values.name} を新規追加しました`, "success");
        setMode("idle");
        setSelectedMs(null);
      } else if (mode === "edit" && selectedMs) {
        const updated = await updateMobileSuit(selectedMs.id, values);
        setSelectedMs(updated);
        showToast(`${values.name} を更新しました`, "success");
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : "エラーが発生しました", "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleDeleteRequest(ms: MasterMobileSuit) {
    setDeleteConfirmMs(ms);
  }

  async function handleDeleteConfirm() {
    if (!deleteConfirmMs) return;
    try {
      await deleteMobileSuit(deleteConfirmMs.id);
      showToast(`${deleteConfirmMs.name} を削除しました`, "success");
      if (selectedMs?.id === deleteConfirmMs.id) {
        setSelectedMs(null);
        setMode("idle");
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : "削除に失敗しました", "error");
    } finally {
      setDeleteConfirmMs(null);
    }
  }

  async function handleCloneConfirm(newId: string) {
    if (!cloneSource) return;
    await createMobileSuit({ ...cloneSource, id: newId });
    showToast(`${cloneSource.name} を ID "${newId}" でクローンしました`, "success");
    setCloneSource(null);
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
              ADMIN: MASTER MOBILE SUITS
            </SciFiHeading>
            <p className="text-xs text-[#ffb000]/60 ml-0 sm:ml-5">
              マスター機体データ管理
            </p>
          </div>
          <div className="flex gap-2">
            <SciFiButton variant="secondary" size="sm" onClick={handleNewMs}>
              + 新規追加
            </SciFiButton>
            {selectedMs && mode === "edit" && (
              <SciFiButton
                variant="primary"
                size="sm"
                onClick={() => setCloneSource(selectedMs)}
              >
                Clone &amp; Edit
              </SciFiButton>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 左カラム: 機体一覧 */}
          <div>
            <SciFiPanel variant="primary">
              <div className="p-4">
                <SciFiHeading level={3} className="mb-3 text-base">
                  機体一覧
                </SciFiHeading>
                {isLoading ? (
                  <p className="text-[#ffb000] animate-pulse py-8 text-center">
                    LOADING...
                  </p>
                ) : (
                  <MobileSuitTable
                    mobileSuits={mobileSuits ?? []}
                    selectedId={selectedMs?.id ?? null}
                    onSelect={handleSelectMs}
                    onDelete={handleDeleteRequest}
                  />
                )}
              </div>
            </SciFiPanel>

            {/* レーダーチャート */}
            {selectedMs && mobileSuits && (
              <SciFiPanel variant="primary" className="mt-4">
                <div className="p-4">
                  <SciFiHeading level={3} className="mb-2 text-base">
                    バランス比較
                  </SciFiHeading>
                  <MobileSuitRadarChart
                    selected={selectedMs}
                    allSuits={mobileSuits}
                  />
                </div>
              </SciFiPanel>
            )}
          </div>

          {/* 右カラム: 編集フォーム */}
          <div>
            {(mode === "edit" || mode === "create") ? (
              <SciFiPanel variant="secondary">
                <div className="p-4">
                  <SciFiHeading level={3} className="mb-3 text-base">
                    {mode === "create" ? "新規機体追加" : `編集: ${selectedMs?.name}`}
                  </SciFiHeading>
                  <MobileSuitEditForm
                    initialData={mode === "edit" ? selectedMs : null}
                    lockId={mode === "edit"}
                    onSubmit={handleSubmit}
                    onCancel={handleCancel}
                    isSubmitting={isSubmitting}
                  />
                </div>
              </SciFiPanel>
            ) : (
              <SciFiPanel variant="primary">
                <div className="p-4 flex items-center justify-center h-48">
                  <p className="text-[#00ff41]/40 text-sm text-center">
                    機体を選択するか「新規追加」ボタンを押してください
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
      {deleteConfirmMs && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-[#050505] border border-red-500/50 p-6 w-full max-w-sm font-mono text-[#00ff41]">
            <h2 className="text-base font-bold text-red-400 mb-3">削除確認</h2>
            <p className="text-sm text-[#00ff41]/80 mb-5">
              <span className="text-red-300 font-bold">{deleteConfirmMs.name}</span> を削除しますか？
              この操作は取り消せません。
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleDeleteConfirm}
                className="flex-1 bg-red-900/30 border border-red-500/60 text-red-400 py-2 text-sm font-bold hover:bg-red-900/50"
              >
                削除する
              </button>
              <button
                onClick={() => setDeleteConfirmMs(null)}
                className="flex-1 border border-[#00ff41]/30 text-[#00ff41]/60 py-2 text-sm hover:border-[#00ff41]/60"
              >
                キャンセル
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Clone ダイアログ */}
      {cloneSource && (
        <CloneDialog
          source={cloneSource}
          onConfirm={handleCloneConfirm}
          onClose={() => setCloneSource(null)}
        />
      )}
    </main>
  );
}
