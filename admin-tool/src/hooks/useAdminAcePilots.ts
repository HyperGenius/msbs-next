/* admin-tool/src/hooks/useAdminAcePilots.ts */
"use client";

import useSWR from "swr";
import { AcePilot, AcePilotCreate, AcePilotUpdate } from "@/types/admin";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "";

const ENDPOINT = `${API_BASE_URL}/api/admin/ace-pilots`;

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

/** FastAPI の detail（文字列 or バリデーションエラー配列）を表示用の文字列にする */
function formatDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d)))
      .join(", ");
  }
  return fallback;
}

/**
 * 管理者用エースパイロットのマスターデータを取得・変更する SWR フック
 */
export function useAdminAcePilots() {
  const { data, error, isLoading, mutate } = useSWR<AcePilot[]>(ENDPOINT, adminFetcher);

  /**
   * 新規エースを追加する（楽観的更新）
   */
  async function createAcePilot(payload: AcePilotCreate): Promise<AcePilot> {
    const optimisticData = data ? [...data, payload] : [payload];

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
          const body = await res.json().catch(() => ({}));
          throw new Error(formatDetail(body.detail, `Create failed: ${res.status}`));
        }
        const created: AcePilot = await res.json();
        return data ? [...data, created] : [created];
      },
      { optimisticData, rollbackOnError: true }
    ).then((list) => {
      const latest = list?.find((ace) => ace.id === payload.id);
      if (!latest) throw new Error("Unexpected: created item not found in cache");
      return latest;
    });
  }

  /**
   * 既存エースを更新する（楽観的更新）
   */
  async function updateAcePilot(aceId: string, payload: AcePilotUpdate): Promise<AcePilot> {
    const optimisticData = data?.map((ace) => (ace.id === aceId ? { ...ace, ...payload } : ace));

    return mutate(
      async () => {
        const res = await fetch(`${ENDPOINT}/${aceId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": ADMIN_API_KEY,
          },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(formatDetail(body.detail, `Update failed: ${res.status}`));
        }
        const updated: AcePilot = await res.json();
        return data?.map((ace) => (ace.id === aceId ? updated : ace)) ?? [updated];
      },
      { optimisticData, rollbackOnError: true }
    ).then((list) => {
      const latest = list?.find((ace) => ace.id === aceId);
      if (!latest) throw new Error("Unexpected: updated item not found in cache");
      return latest;
    });
  }

  /**
   * エースを削除する（楽観的更新）
   */
  async function deleteAcePilot(aceId: string): Promise<void> {
    const optimisticData = data?.filter((ace) => ace.id !== aceId);

    await mutate(
      async () => {
        const res = await fetch(`${ENDPOINT}/${aceId}`, {
          method: "DELETE",
          headers: { "X-API-Key": ADMIN_API_KEY },
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(formatDetail(body.detail, `Delete failed: ${res.status}`));
        }
        return data?.filter((ace) => ace.id !== aceId) ?? [];
      },
      { optimisticData, rollbackOnError: true }
    );
  }

  return {
    acePilots: data,
    isLoading,
    isError: error,
    mutate,
    createAcePilot,
    updateAcePilot,
    deleteAcePilot,
  };
}
