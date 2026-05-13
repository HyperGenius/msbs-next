/* frontend/src/hooks/usePlayerWeapons.ts */
"use client";

import useSWR from "swr";
import { useAuth } from "@clerk/nextjs";
import { PlayerWeapon } from "@/types/battle";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

/**
 * SWR キーを認証状態に応じて生成するヘルパー
 */
function authKey(url: string, isLoaded: boolean, isSignedIn: boolean | undefined): string | null {
  if (!isLoaded || !isSignedIn) return null;
  return url;
}

/**
 * Clerk トークンを使う認証 fetcher
 */
function useAuthFetcher() {
  const { getToken } = useAuth();
  return async (url: string) => {
    const token = await getToken();
    const res = await fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      const err = Object.assign(new Error("Fetch failed"), { status: res.status });
      throw err;
    }
    return res.json();
  };
}

/**
 * ログインユーザーの所有武器インスタンス一覧を取得する SWR hook
 *
 * @param unequippedOnly true の場合、未装備の武器のみ取得する
 */
export function usePlayerWeapons(unequippedOnly = false) {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();

  const url = `${API_BASE_URL}/api/player-weapons${unequippedOnly ? "?unequipped=true" : ""}`;

  const { data, error, isLoading, mutate } = useSWR<PlayerWeapon[]>(
    authKey(url, isLoaded, isSignedIn),
    authFetcher
  );

  return {
    playerWeapons: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
    mutate,
  };
}
