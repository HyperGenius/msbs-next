/* frontend/src/services/api.ts */
import useSWR from "swr";
import { MobileSuit, MobileSuitUpdate } from "@/types/battle";

// Backend API Base URL
const API_BASE_URL = "http://127.0.0.1:8000";

/**
 * Get auth token from Clerk (client-side only)
 */
async function getAuthToken(): Promise<string | null> {
  if (typeof window !== 'undefined') {
    // Client-side: get token from window.Clerk
    const clerk = (window as any).Clerk;
    if (clerk && clerk.session) {
      return await clerk.session.getToken();
    }
  }
  return null;
}

/**
 * SWR用のfetcher関数
 */
const fetcher = async (url: string) => {
  const token = await getAuthToken();
  const headers: HeadersInit = {};
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(url, { headers });
  if (!res.ok) {
    throw new Error(`Failed to fetch data from ${url}: ${res.status} ${res.statusText}`);
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
