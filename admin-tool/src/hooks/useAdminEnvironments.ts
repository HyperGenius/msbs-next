"use client";

import useSWR from "swr";
import { MasterEnvironment, MasterEnvironmentUpdate } from "@/types/admin";
import { adminFetcher, adminRequest, adminUrl } from "@/lib/adminApi";

const ENDPOINT = adminUrl("/environments");

const sortById = (list: MasterEnvironment[]) =>
  [...list].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));

/**
 * 環境タイプを取得・変更する SWR フック。
 * 保存後は backend の返した値でキャッシュを置き換える（環境ID順に並べ直す）。
 */
export function useAdminEnvironments() {
  const { data, error, isLoading, mutate } = useSWR<MasterEnvironment[]>(ENDPOINT, adminFetcher);

  async function createEnvironment(payload: MasterEnvironment): Promise<MasterEnvironment> {
    const created = await adminRequest<MasterEnvironment>(ENDPOINT, "POST", payload);
    await mutate(sortById([...(data ?? []), created]), { revalidate: false });
    return created;
  }

  async function updateEnvironment(
    environmentId: string,
    payload: MasterEnvironmentUpdate
  ): Promise<MasterEnvironment> {
    const updated = await adminRequest<MasterEnvironment>(`${ENDPOINT}/${environmentId}`, "PUT", payload);
    await mutate(
      (data ?? []).map((e) => (e.id === environmentId ? updated : e)),
      { revalidate: false }
    );
    return updated;
  }

  async function deleteEnvironment(environmentId: string): Promise<void> {
    await adminRequest<void>(`${ENDPOINT}/${environmentId}`, "DELETE");
    await mutate(
      (data ?? []).filter((e) => e.id !== environmentId),
      { revalidate: false }
    );
  }

  return {
    environments: data,
    isLoading,
    isError: error,
    createEnvironment,
    updateEnvironment,
    deleteEnvironment,
  };
}
