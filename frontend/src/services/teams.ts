import useSWR from "swr";
import { useAuth } from "@clerk/nextjs";
import { Team, TeamEntryRequest, TeamEntryResponse } from "@/types/battle";
import { API_BASE_URL, getAuthToken, useAuthFetcher, authKey } from "./auth";

/** 現在所属しているチーム情報を取得するSWRフック */
export function useCurrentTeam() {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading, mutate } = useSWR<Team | null>(
    authKey(`${API_BASE_URL}/api/teams/current`, isLoaded, isSignedIn),
    authFetcher,
    { refreshInterval: 5000 }
  );

  return {
    team: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
    mutate,
  };
}

/**
 * チームステータスを5秒ごとにポーリングするSWRフック
 * メンバーの参加・Ready状態をリアルタイムに近い形で画面に反映させる
 */
export function useTeamStatus() {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading, mutate } = useSWR<Team | null>(
    authKey(`${API_BASE_URL}/api/teams/current`, isLoaded, isSignedIn),
    authFetcher,
    { refreshInterval: 5000 }
  );

  return {
    team: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
    mutate,
  };
}

/** 新しいチームを作成する */
export async function createTeam(name: string): Promise<Team> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/teams/create`, {
    method: "POST",
    headers,
    body: JSON.stringify({ name }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create team: ${res.status}`);
  }

  return res.json();
}

/** フレンドをチームに招待する */
export async function inviteTeamMember(teamId: string, userId: string): Promise<Team> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/teams/${teamId}/invite`, {
    method: "POST",
    headers,
    body: JSON.stringify({ user_id: userId }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to invite member: ${res.status}`);
  }

  return res.json();
}

/** 自分のReady状態をトグルする（Ready ↔ 未Ready） */
export async function toggleTeamReady(teamId: string): Promise<Team> {
  const token = await getAuthToken();
  const headers: HeadersInit = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/teams/${teamId}/ready`, {
    method: "POST",
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to toggle ready: ${res.status}`);
  }

  return res.json();
}

/** チームから離脱する。オーナーが離脱した場合はチームが解散になる */
export async function leaveTeam(teamId: string): Promise<void> {
  const token = await getAuthToken();
  const headers: HeadersInit = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/teams/${teamId}/leave`, {
    method: "DELETE",
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to leave team: ${res.status}`);
  }
}

/** チーム全員で一括バトルエントリーする */
export async function teamEntry(request: TeamEntryRequest): Promise<TeamEntryResponse> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/teams/entry`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to team entry: ${res.status}`);
  }

  return res.json();
}
