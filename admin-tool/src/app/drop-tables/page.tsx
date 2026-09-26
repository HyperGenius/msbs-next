"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useAdminDropTable } from "@/hooks/useAdminDropTable";
import DropTableForm from "@/components/admin/DropTableForm";
import { DropTableFormValues, toDropTableUpdate } from "@/lib/dropTable";
import { SciFiPanel, SciFiHeading } from "@/components/ui";

interface Toast {
  message: string;
  type: "success" | "error";
}

export default function AdminDropTablesPage() {
  const { dropTable, isLoading, isError, saveDropTable } = useAdminDropTable();
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
      showToast("ドロップテーブルを保存しました", "success");
    } catch (e) {
      showToast(e instanceof Error ? e.message : "保存に失敗しました", "error");
    } finally {
      setIsSubmitting(false);
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
              ADMIN: DROP TABLES
            </SciFiHeading>
            <p className="text-xs text-[#ffb000]/60 ml-0 sm:ml-5">定期バトルのドロップテーブル</p>
          </div>
          <Link href="/" className="text-xs text-[#00ff41]/60 hover:text-[#00ff41]">
            ← トップへ
          </Link>
        </div>

        <SciFiPanel variant="primary">
          <div className="p-4">
            {isLoading || !dropTable ? (
              <p className="text-[#ffb000] animate-pulse py-8 text-center">LOADING...</p>
            ) : (
              <DropTableForm initialData={dropTable} onSubmit={handleSubmit} isSubmitting={isSubmitting} />
            )}
          </div>
        </SciFiPanel>
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
