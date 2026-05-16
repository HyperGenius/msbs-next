import useSWR from "swr";
import { useAuth } from "@clerk/nextjs";
import { Mission, BattleResult, BattleLog } from "@/types/battle";
import { API_BASE_URL, getAuthToken, fetcher, useAuthFetcher, authKey } from "./auth";

/** ミッション一覧を取得するSWRフック（認証不要・パブリック） */
export function useMissions() {
  const { data, error, isLoading, mutate } = useSWR<Mission[]>(
    `${API_BASE_URL}/api/missions`,
    fetcher
  );

  return {
    missions: data,
    isLoading,
    isError: error,
    mutate,
  };
}

/** 未読のバトル結果一覧を取得するSWRフック */
export function useUnreadBattleResults() {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading, mutate } = useSWR<BattleResult[]>(
    authKey(`${API_BASE_URL}/api/battles/unread`, isLoaded, isSignedIn),
    authFetcher
  );

  return {
    unreadBattles: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
    mutate,
  };
}

/** 指定バトルを既読状態にする */
export async function markBattleAsRead(battleId: string): Promise<void> {
  const token = await getAuthToken();
  const headers: HeadersInit = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/battles/${battleId}/read`, {
    method: "POST",
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to mark battle as read: ${res.status} ${res.statusText}`);
  }
}

/** バトル履歴を取得するSWRフック。limit件数分だけ取得する（デフォルト50件） */
export function useBattleHistory(limit: number = 50) {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading, mutate } = useSWR<BattleResult[]>(
    authKey(`${API_BASE_URL}/api/battles?limit=${limit}`, isLoaded, isSignedIn),
    authFetcher
  );

  return {
    battles: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
    mutate,
  };
}

/** 特定バトルの詳細を取得するSWRフック。battleIdがnullの場合はフェッチしない */
export function useBattleDetail(battleId: string | null) {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading } = useSWR<BattleResult>(
    battleId ? authKey(`${API_BASE_URL}/api/battles/${battleId}`, isLoaded, isSignedIn) : null,
    authFetcher
  );

  return {
    battle: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
  };
}

/** バトルリプレイ用ログを取得するSWRフック。battleResultIdがnullの場合はフェッチしない */
export function useBattleLogs(battleResultId: string | null) {
  const { data, error, isLoading } = useSWR<BattleLog[]>(
    battleResultId ? `${API_BASE_URL}/api/battles/${battleResultId}/logs` : null,
    fetcher
  );

  return {
    logs: data,
    isLoading,
    isError: error,
  };
}
