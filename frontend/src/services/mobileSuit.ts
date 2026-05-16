import useSWR from "swr";
import { useAuth } from "@clerk/nextjs";
import { MobileSuit, MobileSuitUpdate } from "@/types/battle";
import { EnrichedMobileSuit, enrichMobileSuit } from "@/utils/rankUtils";
import { API_BASE_URL, getAuthToken, useAuthFetcher, authKey } from "./auth";

export type { EnrichedMobileSuit };

/** 自分が所有する機体一覧を取得するSWRフック。ランク情報が付与されたEnrichedMobileSuitを返す */
export function useMobileSuits() {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading, mutate } = useSWR<MobileSuit[]>(
    authKey(`${API_BASE_URL}/api/mobile_suits`, isLoaded, isSignedIn),
    authFetcher
  );

  return {
    mobileSuits: data?.map(enrichMobileSuit),
    isLoading: !isLoaded || isLoading,
    isError: error,
    mutate,
  };
}

/** 指定IDの機体データを更新する（ガレージ編集で使用） */
export async function updateMobileSuit(
  id: string,
  updateData: MobileSuitUpdate
): Promise<MobileSuit> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/mobile_suits/${id}`, {
    method: "PUT",
    headers,
    body: JSON.stringify(updateData),
  });

  if (!res.ok) {
    throw new Error(`Failed to update mobile suit ${id}: ${res.status} ${res.statusText}`);
  }

  return res.json();
}
