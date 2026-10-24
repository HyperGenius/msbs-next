"use client";

import useSWR from "swr";
import type { AdminOwnedMobileSuit, AdminPlayerPilot } from "@/types/admin";
import { adminFetcher, adminUrl } from "@/lib/adminApi";

/** プレイヤーのパイロットを名前の部分一致で引く（読み取り専用） */
export function useAdminPlayers(name: string) {
  const query = name.trim();
  const params = new URLSearchParams(query ? { name: query } : {});
  const { data, error, isLoading } = useSWR<AdminPlayerPilot[]>(
    adminUrl(`/players${query ? `?${params}` : ""}`),
    adminFetcher,
    { keepPreviousData: true }
  );
  return { players: data ?? [], error, isLoading };
}

/** パイロットの所有機（読み取り専用）。pilotId が無ければ取得しない */
export function useAdminPlayerMobileSuits(pilotId: string | null) {
  const { data, error, isLoading } = useSWR<AdminOwnedMobileSuit[]>(
    pilotId ? adminUrl(`/players/${encodeURIComponent(pilotId)}/mobile-suits`) : null,
    adminFetcher
  );
  return { mobileSuits: data ?? [], error, isLoading };
}
