/* frontend/src/services/api.ts */
import useSWR from "swr";
import { MobileSuit, MobileSuitUpdate } from "@/types/battle";

// Backend API Base URL
const API_BASE_URL = "http://127.0.0.1:8000";

/**
 * SWR用のfetcher関数
 */
const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error("Failed to fetch data");
  }
  return res.json();
};

/**
 * 機体一覧を取得するSWRフック
 */
export function useMobileSuits() {
  const { data, error, isLoading, mutate } = useSWR<MobileSuit[]>(
    `${API_BASE_URL}/api/mobile_suits`,
    fetcher
  );

  return {
    mobileSuits: data,
    isLoading,
    isError: error,
    mutate,
  };
}

/**
 * 機体データを更新する関数
 */
export async function updateMobileSuit(
  id: string,
  updateData: MobileSuitUpdate
): Promise<MobileSuit> {
  const res = await fetch(`${API_BASE_URL}/api/mobile_suits/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(updateData),
  });

  if (!res.ok) {
    throw new Error("Failed to update mobile suit");
  }

  return res.json();
}
