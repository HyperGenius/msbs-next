"use client";

import useSWR from "swr";
import { MasterTheater, MasterTheaterUpdate, TheaterRotationSlot } from "@/types/admin";
import { adminFetcher, adminRequest, adminUrl } from "@/lib/adminApi";
import { sortByRotation } from "@/lib/theater";

const ENDPOINT = adminUrl("/theaters");

export const ROTATION_DAYS = 14;
const ROTATION_ENDPOINT = `${ENDPOINT}/rotation?days=${ROTATION_DAYS}`;

/**
 * 戦域と、今後のローテーションを取得・変更する SWR フック。
 * 戦域を保存・削除したら、ローテーションを取り直す。
 */
export function useAdminTheaters() {
  const { data, error, isLoading, mutate } = useSWR<MasterTheater[]>(ENDPOINT, adminFetcher);
  const rotation = useSWR<TheaterRotationSlot[]>(ROTATION_ENDPOINT, adminFetcher);

  async function createTheater(payload: MasterTheater): Promise<MasterTheater> {
    const created = await adminRequest<MasterTheater>(ENDPOINT, "POST", payload);
    await mutate(sortByRotation([...(data ?? []), created]), { revalidate: false });
    await rotation.mutate();
    return created;
  }

  async function updateTheater(theaterId: string, payload: MasterTheaterUpdate): Promise<MasterTheater> {
    const updated = await adminRequest<MasterTheater>(`${ENDPOINT}/${theaterId}`, "PUT", payload);
    await mutate(
      sortByRotation((data ?? []).map((t) => (t.id === theaterId ? updated : t))),
      { revalidate: false }
    );
    await rotation.mutate();
    return updated;
  }

  async function deleteTheater(theaterId: string): Promise<void> {
    await adminRequest<void>(`${ENDPOINT}/${theaterId}`, "DELETE");
    await mutate(
      (data ?? []).filter((t) => t.id !== theaterId),
      { revalidate: false }
    );
    await rotation.mutate();
  }

  return {
    theaters: data,
    isLoading,
    isError: error,
    rotation: rotation.data,
    isRotationLoading: rotation.isLoading,
    isRotationError: rotation.error,
    createTheater,
    updateTheater,
    deleteTheater,
  };
}
