import useSWR from "swr";
import { useAuth } from "@clerk/nextjs";
import { EntryStatusResponse, BattleEntry } from "@/types/battle";
import { API_BASE_URL, getAuthToken, fetcher, useAuthFetcher, authKey } from "./auth";

/** 自分のエントリー状況（エントリー済みか・次回バトルルーム情報）を取得するSWRフック */
export function useEntryStatus() {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading, mutate } = useSWR<EntryStatusResponse>(
    authKey(`${API_BASE_URL}/api/entries/status`, isLoaded, isSignedIn),
    authFetcher
  );

  return {
    entryStatus: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
    mutate,
  };
}

/** 現在のエントリー総数を10秒ごとに自動更新するSWRフック（ロビー画面の待機人数表示に使用） */
export function useEntryCount() {
  const { data, error, isLoading, mutate } = useSWR<{ count: number }>(
    `${API_BASE_URL}/api/entries/count`,
    fetcher,
    { refreshInterval: 10000 }
  );

  return {
    entryCount: data?.count ?? 0,
    isLoading,
    isError: error,
    mutate,
  };
}

/** 指定機体IDでバトルにエントリーする */
export async function entryBattle(mobileSuitId: string): Promise<BattleEntry> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/entries`, {
    method: "POST",
    headers,
    body: JSON.stringify({ mobile_suit_id: mobileSuitId }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create entry: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/** エントリーをキャンセルする */
export async function cancelEntry(): Promise<void> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/entries`, {
    method: "DELETE",
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to cancel entry: ${res.status} ${res.statusText}`);
  }
}
