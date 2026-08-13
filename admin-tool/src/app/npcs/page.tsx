/* admin-tool/src/app/npcs/page.tsx */
"use client";

import { useState } from "react";
import { useAdminNpcs, useAdminNpcDetail } from "@/hooks/useAdminNpcs";
import { NpcPilot } from "@/types/admin";
import NpcTable from "@/components/admin/NpcTable";
import NpcEditForm, { NpcPilotFormValues } from "@/components/admin/NpcEditForm";
import { SciFiPanel, SciFiHeading } from "@/components/ui";

interface Toast {
  message: string;
  type: "success" | "error";
}

export default function AdminNpcsPage() {
  const { npcs, isLoading, isError, updateNpc, updateNpcMobileSuit, mutate } = useAdminNpcs();

  const [selectedNpc, setSelectedNpc] = useState<NpcPilot | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

  const { npc: npcDetail, isLoading: isDetailLoading, mutate: mutateDetail } = useAdminNpcDetail(
    selectedNpc?.id ?? null
  );

  function showToast(message: string, type: "success" | "error") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }

  function handleSelectNpc(npc: NpcPilot) {
    setSelectedNpc(npc);
  }

  async function handleSubmitPilot(values: NpcPilotFormValues) {
    if (!selectedNpc) return;
    setIsSubmitting(true);
    try {
      await updateNpc(selectedNpc.id, values);
      await mutateDetail();
      showToast(`${selectedNpc.name} を更新しました`, "success");
    } catch (e) {
      showToast(e instanceof Error ? e.message : "エラーが発生しました", "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmitMobileSuit(
    msId: string,
    payload: { name?: string; max_hp?: number; armor?: number; mobility?: number }
  ) {
    if (!selectedNpc) return;
    try {
      await updateNpcMobileSuit(selectedNpc.id, msId, payload);
      await mutateDetail();
      await mutate();
      showToast("機体ステータスを更新しました", "success");
    } catch (e) {
      showToast(e instanceof Error ? e.message : "エラーが発生しました", "error");
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
        <div className="mb-6 border-b-2 border-[#ffb000]/30 pb-4">
          <SciFiHeading level={2} variant="secondary" className="text-xl sm:text-2xl">
            ADMIN: NPC PILOTS
          </SciFiHeading>
          <p className="text-xs text-[#ffb000]/60 ml-0 sm:ml-5">
            NPCパイロットデータ管理（is_npc=True）
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 左カラム: NPC一覧 */}
          <div>
            <SciFiPanel variant="primary">
              <div className="p-4">
                <SciFiHeading level={3} className="mb-3 text-base">
                  NPC一覧
                </SciFiHeading>
                {isLoading ? (
                  <p className="text-[#ffb000] animate-pulse py-8 text-center">LOADING...</p>
                ) : (
                  <NpcTable npcs={npcs ?? []} selectedId={selectedNpc?.id ?? null} onSelect={handleSelectNpc} />
                )}
              </div>
            </SciFiPanel>
          </div>

          {/* 右カラム: 編集フォーム */}
          <div>
            {selectedNpc ? (
              <SciFiPanel variant="secondary">
                <div className="p-4">
                  <SciFiHeading level={3} className="mb-3 text-base">
                    編集: {selectedNpc.name}
                  </SciFiHeading>
                  {isDetailLoading || !npcDetail ? (
                    <p className="text-[#ffb000] animate-pulse py-8 text-center">LOADING...</p>
                  ) : (
                    <NpcEditForm
                      npc={npcDetail}
                      onSubmitPilot={handleSubmitPilot}
                      onSubmitMobileSuit={handleSubmitMobileSuit}
                      isSubmitting={isSubmitting}
                    />
                  )}
                </div>
              </SciFiPanel>
            ) : (
              <SciFiPanel variant="primary">
                <div className="p-4 flex items-center justify-center h-48">
                  <p className="text-[#00ff41]/40 text-sm text-center">NPCを選択してください</p>
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
    </main>
  );
}
