"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useAdminTechnologies } from "@/hooks/useAdminTechnologies";
import { MasterTechnology } from "@/types/admin";
import { TechnologyFormValues, toTechnologyPayload } from "@/lib/technology";
import TechnologyTable from "@/components/admin/TechnologyTable";
import TechnologyEditForm from "@/components/admin/TechnologyEditForm";
import { SciFiPanel, SciFiHeading, SciFiButton } from "@/components/ui";

type Mode = "idle" | "edit" | "create";

interface Toast {
  message: string;
  type: "success" | "error";
}

export default function AdminTechnologiesPage() {
  const { technologies, isLoading, isError, createTechnology, updateTechnology, deleteTechnology } =
    useAdminTechnologies();

  const [selected, setSelected] = useState<MasterTechnology | null>(null);
  const [mode, setMode] = useState<Mode>("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<MasterTechnology | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  function showToast(message: string, type: "success" | "error") {
    // 連続して保存したとき、前のトーストのタイマーで新しいトーストが消えないようにする。
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast({ message, type });
    toastTimerRef.current = setTimeout(() => setToast(null), 4000);
  }

  async function handleSubmit(values: TechnologyFormValues) {
    setIsSubmitting(true);
    try {
      const payload = toTechnologyPayload(values);
      if (mode === "create") {
        const created = await createTechnology(payload);
        setSelected(created);
        setMode("edit");
        showToast(`${created.name} を追加しました`, "success");
      } else if (mode === "edit" && selected) {
        const { id: _id, ...update } = payload;
        const updated = await updateTechnology(selected.id, update);
        setSelected(updated);
        showToast(`${updated.name} を更新しました`, "success");
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : "保存に失敗しました", "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    try {
      await deleteTechnology(deleteTarget.id);
      showToast(`${deleteTarget.name} を削除しました`, "success");
      if (selected?.id === deleteTarget.id) {
        setSelected(null);
        setMode("idle");
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : "削除に失敗しました", "error");
    } finally {
      setDeleteTarget(null);
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
        <div className="mb-6 border-b-2 border-[#ffb000]/30 pb-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <SciFiHeading level={2} variant="secondary" className="text-xl sm:text-2xl">
              ADMIN: TECHNOLOGIES
            </SciFiHeading>
            <p className="text-xs text-[#ffb000]/60 ml-0 sm:ml-5">
              技術マスター（技術断片と技術Lv）
            </p>
          </div>
          <div className="flex items-center gap-3">
            <SciFiButton
              variant="secondary"
              size="sm"
              onClick={() => {
                setSelected(null);
                setMode("create");
              }}
            >
              + 新規追加
            </SciFiButton>
            <Link href="/" className="text-xs text-[#00ff41]/60 hover:text-[#00ff41]">
              ← トップへ
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SciFiPanel variant="primary">
            <div className="p-4">
              <SciFiHeading level={3} className="mb-3 text-base">
                技術一覧
              </SciFiHeading>
              {isLoading ? (
                <p className="text-[#ffb000] animate-pulse py-8 text-center">LOADING...</p>
              ) : (
                <TechnologyTable
                  technologies={technologies ?? []}
                  selectedId={selected?.id ?? null}
                  onSelect={(tech) => {
                    setSelected(tech);
                    setMode("edit");
                  }}
                  onDelete={setDeleteTarget}
                />
              )}
              <p className="mt-3 text-xs text-[#00ff41]/40">
                購入条件（機体・武器の設計図設定）やドロップテーブルから参照されている技術は削除できない。
              </p>
            </div>
          </SciFiPanel>

          {mode === "idle" ? (
            <SciFiPanel variant="primary">
              <div className="p-4 flex items-center justify-center h-48">
                <p className="text-[#00ff41]/40 text-sm text-center">
                  技術を選択するか「新規追加」ボタンを押してください
                </p>
              </div>
            </SciFiPanel>
          ) : (
            <SciFiPanel variant="secondary">
              <div className="p-4">
                <SciFiHeading level={3} className="mb-3 text-base">
                  {mode === "create" ? "新規技術追加" : `編集: ${selected?.name}`}
                </SciFiHeading>
                <TechnologyEditForm
                  initialData={mode === "edit" ? selected : null}
                  onSubmit={handleSubmit}
                  onCancel={() => setMode("idle")}
                  isSubmitting={isSubmitting}
                />
              </div>
            </SciFiPanel>
          )}
        </div>
      </div>

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

      {deleteTarget && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-[#050505] border border-red-500/50 p-6 w-full max-w-sm font-mono text-[#00ff41]">
            <h2 className="text-base font-bold text-red-400 mb-3">削除確認</h2>
            <p className="text-sm text-[#00ff41]/80 mb-5">
              <span className="text-red-300 font-bold">{deleteTarget.name}</span>{" "}
              を削除しますか？プレイヤーの累計断片数も削除されます。この操作は取り消せません。
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleDeleteConfirm}
                className="flex-1 bg-red-900/30 border border-red-500/60 text-red-400 py-2 text-sm font-bold hover:bg-red-900/50"
              >
                削除する
              </button>
              <button
                onClick={() => setDeleteTarget(null)}
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
