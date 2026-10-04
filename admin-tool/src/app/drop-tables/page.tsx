"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useAdminDropTable, useAdminDropTableScopes } from "@/hooks/useAdminDropTable";
import DropTableForm from "@/components/admin/DropTableForm";
import { DropTableFormValues, toDropTableUpdate } from "@/lib/dropTable";
import { DropTableScopeSummary } from "@/types/admin";
import { SciFiPanel, SciFiHeading, SciFiButton } from "@/components/ui";

interface Toast {
  message: string;
  type: "success" | "error";
}

function scopeId(scope: Pick<DropTableScopeSummary, "scope_type" | "scope_key">): string {
  return `${scope.scope_type}:${scope.scope_key}`;
}

function ScopeStatus({ scope }: { scope: DropTableScopeSummary }) {
  if (scope.scope_type === "BATCH") {
    return <span className="text-[#00ff41]/50">{scope.has_table ? "作成済み" : "未作成"}</span>;
  }
  return (
    <span className="flex gap-1">
      {!scope.is_active && <span className="px-1 border border-[#00ff41]/30 text-[#00ff41]/40">無効</span>}
      {scope.has_table ? (
        <span className="text-[#00ff41]/50">戦域のテーブル</span>
      ) : (
        <span className="text-[#ffb000]/70">共通テーブルを使用中</span>
      )}
    </span>
  );
}

export default function AdminDropTablesPage() {
  const { scopes, isError: isScopesError, reloadScopes } = useAdminDropTableScopes();
  const [selectedId, setSelectedId] = useState<string>(scopeId({ scope_type: "BATCH", scope_key: "default" }));
  const selected = scopes?.find((scope) => scopeId(scope) === selectedId) ?? null;
  const { dropTable, isLoading, isError, saveDropTable, deleteDropTable } = useAdminDropTable(selected);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);
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

  async function handleSubmit(values: DropTableFormValues) {
    setIsSubmitting(true);
    try {
      await saveDropTable(toDropTableUpdate(values));
      await reloadScopes();
      showToast(`${selected?.label ?? "ドロップテーブル"}を保存しました`, "success");
    } catch (e) {
      showToast(e instanceof Error ? e.message : "保存に失敗しました", "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!selected) return;
    if (!window.confirm(`${selected.label}のテーブルを削除し、共通テーブルを使う状態に戻します。よろしいですか？`)) {
      return;
    }
    setIsSubmitting(true);
    try {
      await deleteDropTable();
      await reloadScopes();
      showToast(`${selected.label}を共通テーブルに戻しました`, "success");
    } catch (e) {
      showToast(e instanceof Error ? e.message : "削除に失敗しました", "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isError || isScopesError) {
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
              ADMIN: DROP TABLES
            </SciFiHeading>
            <p className="text-xs text-[#ffb000]/60 ml-0 sm:ml-5">定期バトルのドロップテーブル（共通・戦域ごと）</p>
          </div>
          <Link href="/" className="text-xs text-[#00ff41]/60 hover:text-[#00ff41]">
            ← トップへ
          </Link>
        </div>

        <div className="mb-6 border border-[#ffb000]/30 bg-[#ffb000]/5 p-3 text-xs text-[#ffb000]/80 space-y-1">
          <p>定期バトルは、ルームの戦域のテーブルで抽選する。戦域のテーブルが無ければ共通テーブルで抽選する。</p>
          <p>戦域のテーブルにエントリーが無いと、その戦域ではドロップしない（共通テーブルは使わない）。</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[16rem_1fr] gap-6">
          <SciFiPanel variant="primary">
            <div className="p-4">
              <SciFiHeading level={3} className="mb-3 text-base">
                テーブル
              </SciFiHeading>
              {!scopes ? (
                <p className="text-[#ffb000] animate-pulse py-4 text-center">LOADING...</p>
              ) : (
                <ul className="space-y-1">
                  {scopes.map((scope) => {
                    const id = scopeId(scope);
                    const isSelected = id === selectedId;
                    return (
                      <li key={id}>
                        <button
                          type="button"
                          onClick={() => setSelectedId(id)}
                          className={`w-full text-left border px-2 py-1.5 text-sm ${
                            isSelected
                              ? "border-[#00ff41] bg-[#00ff41]/10"
                              : "border-[#00ff41]/20 hover:border-[#00ff41]/60"
                          }`}
                        >
                          <span className={scope.is_active ? "" : "text-[#00ff41]/50"}>{scope.label}</span>
                          <span className="block text-[10px]">
                            <ScopeStatus scope={scope} />
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </SciFiPanel>

          <SciFiPanel variant="primary">
            <div className="p-4 space-y-4">
              {selected?.scope_type === "THEATER" && dropTable && (
                <div className="flex flex-wrap items-center gap-3 text-xs">
                  {dropTable.uses_common_table ? (
                    <p className="text-[#ffb000]">
                      共通テーブルを使用中。下の値は共通テーブルの内容。保存すると、この内容で{selected.label}のテーブルを作成する。
                    </p>
                  ) : (
                    <>
                      <p className="text-[#00ff41]/70">{selected.label}のテーブルで抽選する。</p>
                      <SciFiButton
                        type="button"
                        variant="secondary"
                        size="sm"
                        disabled={isSubmitting}
                        onClick={handleDelete}
                      >
                        共通テーブルに戻す
                      </SciFiButton>
                    </>
                  )}
                </div>
              )}
              {selected?.scope_type === "BATCH" && (
                <p className="text-xs text-[#00ff41]/70">
                  戦域のテーブルが無い戦域と、戦域なしのルームで使う。
                </p>
              )}
              {isLoading || !dropTable ? (
                <p className="text-[#ffb000] animate-pulse py-8 text-center">LOADING...</p>
              ) : (
                <DropTableForm
                  key={selectedId}
                  initialData={dropTable}
                  onSubmit={handleSubmit}
                  isSubmitting={isSubmitting}
                />
              )}
            </div>
          </SciFiPanel>
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
    </main>
  );
}
