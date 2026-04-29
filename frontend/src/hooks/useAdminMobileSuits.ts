/* frontend/src/hooks/useAdminMobileSuits.ts */
"use client";

import useSWR from "swr";
import { MasterMobileSuit, MasterMobileSuitCreate, MasterMobileSuitUpdate } from "@/types/battle";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "";

const ENDPOINT = `${API_BASE_URL}/api/admin/mobile-suits`;

function adminFetcher(url: string) {
  return fetch(url, {
    headers: { "X-API-Key": ADMIN_API_KEY },
  }).then(async (res) => {
    if (!res.ok) {
      const err = new Error(`Failed to fetch ${url}: ${res.status} ${res.statusText}`) as Error & { status: number };
      err.status = res.status;
      throw err;
    }
    return res.json();
  });
}

/**
 * 管理者用マスター機体データを取得・変更する SWR フック
 */
export function useAdminMobileSuits() {
  const { data, error, isLoading, mutate } = useSWR<MasterMobileSuit[]>(
    ENDPOINT,
    adminFetcher
  );

  /**
   * 新規機体を追加する（楽観的更新）
   */
  async function createMobileSuit(payload: MasterMobileSuitCreate): Promise<MasterMobileSuit> {
    const optimisticData = data ? [...data, payload as MasterMobileSuit] : [payload as MasterMobileSuit];

    return mutate(
      async () => {
        const res = await fetch(ENDPOINT, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": ADMIN_API_KEY,
          },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail.detail || `Create failed: ${res.status}`);
        }
        const created: MasterMobileSuit = await res.json();
        return data ? [...data, created] : [created];
      },
      { optimisticData, rollbackOnError: true }
    ).then((list) => {
      const latest = list?.find((ms) => ms.id === payload.id);
      if (!latest) throw new Error("Unexpected: created item not found in cache");
      return latest;
    });
  }

  /**
   * 既存機体を更新する（楽観的更新）
   */
  async function updateMobileSuit(msId: string, payload: MasterMobileSuitUpdate): Promise<MasterMobileSuit> {
    const optimisticData = data?.map((ms) =>
      ms.id === msId ? { ...ms, ...payload, specs: payload.specs ?? ms.specs } : ms
    );

    return mutate(
      async () => {
        const res = await fetch(`${ENDPOINT}/${msId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": ADMIN_API_KEY,
          },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail.detail || `Update failed: ${res.status}`);
        }
        const updated: MasterMobileSuit = await res.json();
        return data?.map((ms) => (ms.id === msId ? updated : ms)) ?? [updated];
      },
      { optimisticData, rollbackOnError: true }
    ).then((list) => {
      const latest = list?.find((ms) => ms.id === msId);
      if (!latest) throw new Error("Unexpected: updated item not found in cache");
      return latest;
    });
  }

  /**
   * 機体を削除する（楽観的更新）
   */
  async function deleteMobileSuit(msId: string): Promise<void> {
    const optimisticData = data?.filter((ms) => ms.id !== msId);

    await mutate(
      async () => {
        const res = await fetch(`${ENDPOINT}/${msId}`, {
          method: "DELETE",
          headers: { "X-API-Key": ADMIN_API_KEY },
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail.detail || `Delete failed: ${res.status}`);
        }
        return data?.filter((ms) => ms.id !== msId) ?? [];
      },
      { optimisticData, rollbackOnError: true }
    );
  }

  return {
    mobileSuits: data,
    isLoading,
    isError: error,
    mutate,
    createMobileSuit,
    updateMobileSuit,
    deleteMobileSuit,
  };
}
