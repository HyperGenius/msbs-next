"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useAdminEnvironments } from "@/hooks/useAdminEnvironments";
import { MasterEnvironment } from "@/types/admin";
import { EnvironmentFormValues } from "@/lib/theater";
import EnvironmentTable from "@/components/admin/EnvironmentTable";
import EnvironmentEditForm from "@/components/admin/EnvironmentEditForm";
import { SciFiPanel, SciFiHeading, SciFiButton } from "@/components/ui";

type Mode = "idle" | "edit" | "create";

interface Toast {
  message: string;
  type: "success" | "error";
}

export default function AdminEnvironmentsPage() {
  const { environments, isLoading, isError, createEnvironment, updateEnvironment, deleteEnvironment } =
    useAdminEnvironments();

  const [selected, setSelected] = useState<MasterEnvironment | null>(null);
  const [mode, setMode] = useState<Mode>("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<MasterEnvironment | null>(null);
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

  async function handleSubmit(values: EnvironmentFormValues) {
    setIsSubmitting(true);
    try {
      if (mode === "create") {
        const created = await createEnvironment(values);
        setSelected(created);
        setMode("edit");
        showToast(`${created.name} を追加しました`, "success");
      } else if (mode === "edit" && selected) {
        const { id: _id, ...update } = values;
        const updated = await updateEnvironment(selected.id, update);
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
      await deleteEnvironment(deleteTarget.id);
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
              admin-tool の NEXT_PUBLIC_ADMIN_API_KEY・NEXT_PUBLIC_API_URL が正しく設定されているか、
              バックエンドが起動しているか確認してください。
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
              ADMIN: ENVIRONMENTS
            </SciFiHeading>
            <p className="text-xs text-[#ffb000]/60 ml-0 sm:ml-5">環境タイプ（索敵・射撃の効果と地形適正の既定値）</p>
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
            <Link href="/theaters" className="text-xs text-[#00ff41]/60 hover:text-[#00ff41]">
              戦域管理 →
            </Link>
            <Link href="/" className="text-xs text-[#00ff41]/60 hover:text-[#00ff41]">
              ← トップへ
            </Link>
          </div>
        </div>

        <div className="mb-6 border border-[#ffb000]/30 bg-[#ffb000]/5 p-3 text-xs text-[#ffb000]/80 space-y-1">
          <p>
            環境タイプで表せるのは、索敵範囲・射撃の命中率・障害物密度・地形適正の既定ランク・描画プリセットだけ。
            水中でのビーム減衰のような新しい仕組みが必要な環境は、パラメータだけでは表せない（戦闘エンジンの実装が要る）。
          </p>
          <p>
            効果パラメータは戦闘のときにマスターから読む。変更は、作成済みのルームを含めて次の戦闘から反映する。
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SciFiPanel variant="primary">
            <div className="p-4">
              <SciFiHeading level={3} className="mb-3 text-base">
                環境タイプ一覧
              </SciFiHeading>
              {isLoading ? (
                <p className="text-[#ffb000] animate-pulse py-8 text-center">LOADING...</p>
              ) : (
                <EnvironmentTable
                  environments={environments ?? []}
                  selectedId={selected?.id ?? null}
                  onSelect={(environment) => {
                    setSelected(environment);
                    setMode("edit");
                  }}
                  onDelete={setDeleteTarget}
                />
              )}
              <p className="mt-3 text-xs text-[#00ff41]/40">戦域から参照されている環境タイプは削除できない。</p>
            </div>
          </SciFiPanel>

          {mode === "idle" ? (
            <SciFiPanel variant="primary">
              <div className="p-4 flex items-center justify-center h-48">
                <p className="text-[#00ff41]/40 text-sm text-center">
                  環境タイプを選択するか「新規追加」ボタンを押してください
                </p>
              </div>
            </SciFiPanel>
          ) : (
            <SciFiPanel variant="secondary">
              <div className="p-4">
                <SciFiHeading level={3} className="mb-3 text-base">
                  {mode === "create" ? "新規環境タイプ追加" : `編集: ${selected?.name}`}
                </SciFiHeading>
                <EnvironmentEditForm
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
              を削除しますか？機体の地形適正に残った {deleteTarget.id} の設定は消さない。この操作は取り消せません。
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
