"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ROTATION_DAYS, useAdminTheaters } from "@/hooks/useAdminTheaters";
import { useAdminEnvironments } from "@/hooks/useAdminEnvironments";
import { MasterTheater } from "@/types/admin";
import { TheaterFormValues, toTheaterPayload } from "@/lib/theater";
import TheaterTable from "@/components/admin/TheaterTable";
import TheaterEditForm from "@/components/admin/TheaterEditForm";
import TheaterRotationPanel from "@/components/admin/TheaterRotationPanel";
import { SciFiPanel, SciFiHeading, SciFiButton } from "@/components/ui";

type Mode = "idle" | "edit" | "create";

interface Toast {
  message: string;
  type: "success" | "error";
}

export default function AdminTheatersPage() {
  const {
    theaters,
    isLoading,
    isError,
    rotation,
    isRotationLoading,
    isRotationError,
    createTheater,
    updateTheater,
    deleteTheater,
  } = useAdminTheaters();
  const { environments, isError: isEnvironmentsError } = useAdminEnvironments();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<MasterTheater | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 一覧で順番・有効化を変えても最新の値を参照できるよう、IDで引く。
  const selected = theaters?.find((t) => t.id === selectedId) ?? null;

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

  async function handleSubmit(values: TheaterFormValues) {
    setIsSubmitting(true);
    try {
      const payload = toTheaterPayload(values);
      if (mode === "create") {
        const created = await createTheater(payload);
        setSelectedId(created.id);
        setMode("edit");
        showToast(`${created.name} を追加しました`, "success");
      } else if (mode === "edit" && selected) {
        // 順番と有効化は一覧が正。フォームを開いた後に一覧で変えた値を戻さないよう送らない。
        const { id: _id, rotation_order: _order, is_active: _active, ...update } = payload;
        const updated = await updateTheater(selected.id, update);
        showToast(`${updated.name} を更新しました`, "success");
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : "保存に失敗しました", "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleChangeOrder(theater: MasterTheater, rotationOrder: number) {
    try {
      await updateTheater(theater.id, { rotation_order: rotationOrder });
      showToast(`${theater.name} の順番を ${rotationOrder} にしました`, "success");
    } catch (e) {
      showToast(e instanceof Error ? e.message : "保存に失敗しました", "error");
      throw e;
    }
  }

  async function handleToggleActive(theater: MasterTheater, isActive: boolean) {
    try {
      await updateTheater(theater.id, { is_active: isActive });
      showToast(`${theater.name} を${isActive ? "有効" : "無効"}にしました`, "success");
    } catch (e) {
      showToast(e instanceof Error ? e.message : "保存に失敗しました", "error");
      throw e;
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    try {
      await deleteTheater(deleteTarget.id);
      showToast(`${deleteTarget.name} を削除しました`, "success");
      if (selectedId === deleteTarget.id) {
        setSelectedId(null);
        setMode("idle");
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : "削除に失敗しました", "error");
    } finally {
      setDeleteTarget(null);
    }
  }

  if (isError || isEnvironmentsError) {
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
              ADMIN: THEATERS
            </SciFiHeading>
            <p className="text-xs text-[#ffb000]/60 ml-0 sm:ml-5">戦域とローテーション（定期バトル）</p>
          </div>
          <div className="flex items-center gap-3">
            <SciFiButton
              variant="secondary"
              size="sm"
              onClick={() => {
                setSelectedId(null);
                setMode("create");
              }}
            >
              + 新規追加
            </SciFiButton>
            <Link href="/environments" className="text-xs text-[#00ff41]/60 hover:text-[#00ff41]">
              環境タイプ管理 →
            </Link>
            <Link href="/" className="text-xs text-[#00ff41]/60 hover:text-[#00ff41]">
              ← トップへ
            </Link>
          </div>
        </div>

        <div className="mb-6 border border-[#ffb000]/30 bg-[#ffb000]/5 p-3 text-xs text-[#ffb000]/80 space-y-1">
          <p>
            順番・有効化・濃度の変更は、次に作成されるルームから反映する。作成済みの OPEN ルーム（今回）の戦域と濃度は変えない。
          </p>
          <p>戦域の環境タイプと障害物密度は戦闘のときにマスターから読むため、今回のルームにも反映する。</p>
          <p>
            有効な戦域が1つだけのとき、その戦域は無効にも削除にもできない。
            削除すると、その戦域のドロップテーブルも削除する。過去のバトル結果には戦域IDが残る（戦域名の代わりにIDを表示する）。
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-6">
            <SciFiPanel variant="primary">
              <div className="p-4">
                <SciFiHeading level={3} className="mb-3 text-base">
                  戦域一覧
                </SciFiHeading>
                {isLoading ? (
                  <p className="text-[#ffb000] animate-pulse py-8 text-center">LOADING...</p>
                ) : (
                  <TheaterTable
                    theaters={theaters ?? []}
                    environments={environments ?? []}
                    selectedId={selectedId}
                    onSelect={(theater) => {
                      setSelectedId(theater.id);
                      setMode("edit");
                    }}
                    onDelete={setDeleteTarget}
                    onChangeOrder={handleChangeOrder}
                    onToggleActive={handleToggleActive}
                  />
                )}
                <p className="mt-3 text-xs text-[#00ff41]/40">
                  有効な戦域を順番（同じなら ID）の昇順に、開催日ごとに巡回する。
                </p>
              </div>
            </SciFiPanel>

            <SciFiPanel variant="primary">
              <div className="p-4">
                <SciFiHeading level={3} className="mb-3 text-base">
                  今後{ROTATION_DAYS}日のローテーション
                </SciFiHeading>
                <TheaterRotationPanel
                  rotation={rotation}
                  isLoading={isRotationLoading}
                  isError={!!isRotationError}
                />
              </div>
            </SciFiPanel>
          </div>

          {mode === "idle" ? (
            <SciFiPanel variant="primary">
              <div className="p-4 flex items-center justify-center h-48">
                <p className="text-[#00ff41]/40 text-sm text-center">
                  戦域を選択するか「新規追加」ボタンを押してください
                </p>
              </div>
            </SciFiPanel>
          ) : (
            <SciFiPanel variant="secondary">
              <div className="p-4">
                <SciFiHeading level={3} className="mb-3 text-base">
                  {mode === "create" ? "新規戦域追加" : `編集: ${selected?.name}`}
                </SciFiHeading>
                <TheaterEditForm
                  key={mode === "edit" ? selectedId ?? "new" : "new"}
                  initialData={mode === "edit" ? selected : null}
                  theaters={theaters ?? []}
                  environments={environments ?? []}
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
              を削除しますか？ローテーションが変わります。この操作は取り消せません。
              一時的に外すだけなら、一覧で無効にしてください。
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
