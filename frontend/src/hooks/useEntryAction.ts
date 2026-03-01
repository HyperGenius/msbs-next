/* frontend/src/hooks/useEntryAction.ts */
"use client";

import { useState } from "react";
import { MobileSuit } from "@/types/battle";
import { entryBattle, cancelEntry } from "@/services/api";

interface UseEntryActionOptions {
  mobileSuits: MobileSuit[] | undefined;
  mutateEntryStatus: () => void;
  mutateEntryCount: () => void;
}

interface UseEntryActionReturn {
  entryLoading: boolean;
  showEntryModal: boolean;
  setShowEntryModal: (show: boolean) => void;
  handleEntry: () => Promise<void>;
  executeEntry: (mobileSuitId: string) => Promise<void>;
  handleCancelEntry: () => Promise<void>;
}

/**
 * バトルエントリー登録・キャンセル処理を管理するフック。
 */
export function useEntryAction({
  mobileSuits,
  mutateEntryStatus,
  mutateEntryCount,
}: UseEntryActionOptions): UseEntryActionReturn {
  const [entryLoading, setEntryLoading] = useState(false);
  const [showEntryModal, setShowEntryModal] = useState(false);

  const handleEntry = async () => {
    if (!mobileSuits || mobileSuits.length === 0) {
      alert("機体がありません。ガレージで機体を作成してください。");
      return;
    }

    if (mobileSuits.length === 1) {
      await executeEntry(mobileSuits[0].id);
    } else {
      setShowEntryModal(true);
    }
  };

  const executeEntry = async (mobileSuitId: string) => {
    setEntryLoading(true);
    try {
      await entryBattle(mobileSuitId);
      await mutateEntryStatus();
      await mutateEntryCount();
      setShowEntryModal(false);
    } catch (error) {
      console.error("Error creating entry:", error);
      alert(
        `エントリーに失敗しました: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    } finally {
      setEntryLoading(false);
    }
  };

  const handleCancelEntry = async () => {
    setEntryLoading(true);
    try {
      await cancelEntry();
      await mutateEntryStatus();
      await mutateEntryCount();
    } catch (error) {
      console.error("Error cancelling entry:", error);
      alert(
        `キャンセルに失敗しました: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    } finally {
      setEntryLoading(false);
    }
  };

  return {
    entryLoading,
    showEntryModal,
    setShowEntryModal,
    handleEntry,
    executeEntry,
    handleCancelEntry,
  };
}
