/* admin-tool/src/hooks/useAdminNpcs.ts */
"use client";

import useSWR from "swr";
import { NpcPilot, NpcPilotDetail, NpcPilotUpdate, NpcMobileSuitUpdate, NpcMobileSuit } from "@/types/admin";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "";

const ENDPOINT = `${API_BASE_URL}/api/admin/npcs`;

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
 * 管理者用NPC(Pilot)データを取得・変更する SWR フック
 */
export function useAdminNpcs() {
  const { data, error, isLoading, mutate } = useSWR<NpcPilot[]>(ENDPOINT, adminFetcher);

  /**
   * NPCのステータスを更新する（楽観的更新）
   */
  async function updateNpc(pilotId: string, payload: NpcPilotUpdate): Promise<NpcPilotDetail> {
    const optimisticData = data?.map((npc) => (npc.id === pilotId ? { ...npc, ...payload } : npc));

    const res = await fetch(`${ENDPOINT}/${pilotId}`, {
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
    const updated: NpcPilotDetail = await res.json();

    await mutate(data?.map((npc) => (npc.id === pilotId ? updated : npc)) ?? [updated], {
      optimisticData,
      rollbackOnError: true,
      revalidate: false,
    });

    return updated;
  }

  /**
   * NPC所有機体のステータスを更新する（一覧の mobile_suit_count には影響しないため単純呼び出し）
   */
  async function updateNpcMobileSuit(
    pilotId: string,
    msId: string,
    payload: NpcMobileSuitUpdate
  ): Promise<NpcMobileSuit> {
    const res = await fetch(`${ENDPOINT}/${pilotId}/mobile-suits/${msId}`, {
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
    return res.json();
  }

  return {
    npcs: data,
    isLoading,
    isError: error,
    mutate,
    updateNpc,
    updateNpcMobileSuit,
  };
}

/**
 * NPC1体の詳細（所有機体一覧付き）を取得する SWR フック
 */
export function useAdminNpcDetail(pilotId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<NpcPilotDetail>(
    pilotId ? `${ENDPOINT}/${pilotId}` : null,
    adminFetcher
  );

  return {
    npc: data,
    isLoading,
    isError: error,
    mutate,
  };
}
