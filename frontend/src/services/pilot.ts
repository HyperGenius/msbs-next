import useSWR from "swr";
import { useAuth } from "@clerk/nextjs";
import { Pilot } from "@/types/battle";
import { API_BASE_URL, getAuthToken, useAuthFetcher, authKey } from "./auth";

/** ステータスポイント割り振りリクエストの型 */
export interface StatusAllocateRequest {
  sht?: number;
  mel?: number;
  intel?: number;
  ref?: number;
  tou?: number;
  luk?: number;
}

/**
 * 自分のパイロット情報を取得するSWRフック
 * パイロット未登録（404）の場合はisNotFoundフラグを返し、エラーとして扱わない
 */
export function usePilot() {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading, mutate } = useSWR<Pilot>(
    authKey(`${API_BASE_URL}/api/pilots/me`, isLoaded, isSignedIn),
    authFetcher
  );

  const isNotFound = error && (error as { status?: number }).status === 404;

  return {
    pilot: data,
    isLoading: !isLoaded || isLoading,
    isError: error && !isNotFound ? error : undefined,
    isNotFound: !!isNotFound,
    mutate,
  };
}

/** パイロットを新規登録する（オンボーディングのフェーズ4→5で呼び出す） */
export async function registerPilot(
  name: string,
  faction: "FEDERATION" | "ZEON",
  background: string,
  bonusStats: { bonus_sht: number; bonus_mel: number; bonus_int: number; bonus_ref: number; bonus_tou: number; bonus_luk: number }
): Promise<{ pilot: Pilot; mobile_suit_id: string; message: string }> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/pilots/register`, {
    method: "POST",
    headers,
    body: JSON.stringify({ name, faction, background, ...bonusStats }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to register pilot: ${res.status} ${res.statusText}`
    );
  }

  return res.json();
}

/** 未使用のステータスポイントを各ステータスへ割り振る */
export async function allocateStatusPoints(request: StatusAllocateRequest): Promise<Pilot> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // 未指定のステータスは0として送信する（APIが部分更新に対応していないため）
  const body = {
    sht: request.sht ?? 0,
    mel: request.mel ?? 0,
    intel: request.intel ?? 0,
    ref: request.ref ?? 0,
    tou: request.tou ?? 0,
    luk: request.luk ?? 0,
  };

  const res = await fetch(`${API_BASE_URL}/api/pilots/status/allocate`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to allocate status points: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/** パイロット名を変更する */
export async function updatePilotName(name: string): Promise<Pilot> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/pilots/me/name`, {
    method: "PUT",
    headers,
    body: JSON.stringify({ name }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to update pilot name: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * アカウントをリセットする（デバッグ用）
 * 現在のユーザーに紐づく全データ（パイロット・機体・戦績）を削除する
 */
export async function resetAccount(): Promise<void> {
  const token = await getAuthToken();
  const headers: HeadersInit = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/pilots/me`, {
    method: "DELETE",
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to reset account: ${res.status} ${res.statusText}`);
  }
}
