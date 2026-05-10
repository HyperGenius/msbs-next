/* frontend/src/hooks/useAdminWeapons.ts */
"use client";

import useSWR from "swr";
import { MasterWeapon, MasterWeaponCreate, MasterWeaponUpdate } from "@/types/battle";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "";

const ENDPOINT = `${API_BASE_URL}/api/admin/weapons`;

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
 * 管理者用マスター武器データを取得・変更する SWR フック
 */
export function useAdminWeapons() {
  const { data, error, isLoading, mutate } = useSWR<MasterWeapon[]>(
    ENDPOINT,
    adminFetcher
  );

  /**
   * 新規武器を追加する（楽観的更新）
   */
  async function createWeapon(payload: MasterWeaponCreate): Promise<MasterWeapon> {
    const optimisticData = data ? [...data, payload as MasterWeapon] : [payload as MasterWeapon];

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
        const created: MasterWeapon = await res.json();
        return data ? [...data, created] : [created];
      },
      { optimisticData, rollbackOnError: true }
    ).then((list) => {
      const latest = list?.find((w) => w.id === payload.id);
      if (!latest) throw new Error("Unexpected: created item not found in cache");
      return latest;
    });
  }

  /**
   * 既存武器を更新する（楽観的更新）
   */
  async function updateWeapon(weaponId: string, payload: MasterWeaponUpdate): Promise<MasterWeapon> {
    const optimisticData = data?.map((w) =>
      w.id === weaponId ? { ...w, ...payload, weapon: payload.weapon ?? w.weapon } : w
    );

    return mutate(
      async () => {
        const res = await fetch(`${ENDPOINT}/${weaponId}`, {
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
        const updated: MasterWeapon = await res.json();
        return data?.map((w) => (w.id === weaponId ? updated : w)) ?? [updated];
      },
      { optimisticData, rollbackOnError: true }
    ).then((list) => {
      const latest = list?.find((w) => w.id === weaponId);
      if (!latest) throw new Error("Unexpected: updated item not found in cache");
      return latest;
    });
  }

  /**
   * 武器を削除する（楽観的更新）
   */
  async function deleteWeapon(weaponId: string): Promise<void> {
    const optimisticData = data?.filter((w) => w.id !== weaponId);

    await mutate(
      async () => {
        const res = await fetch(`${ENDPOINT}/${weaponId}`, {
          method: "DELETE",
          headers: { "X-API-Key": ADMIN_API_KEY },
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail.detail || `Delete failed: ${res.status}`);
        }
        return data?.filter((w) => w.id !== weaponId) ?? [];
      },
      { optimisticData, rollbackOnError: true }
    );
  }

  return {
    weapons: data,
    isLoading,
    isError: error,
    mutate,
    createWeapon,
    updateWeapon,
    deleteWeapon,
  };
}
