import useSWR from "swr";
import { useAuth } from "@clerk/nextjs";
import { Friend } from "@/types/battle";
import { API_BASE_URL, getAuthToken, useAuthFetcher, authKey } from "./auth";

/** フレンド一覧（承認済み）を取得するSWRフック */
export function useFriends() {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading, mutate } = useSWR<Friend[]>(
    authKey(`${API_BASE_URL}/api/friends/`, isLoaded, isSignedIn),
    authFetcher
  );

  return {
    friends: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
    mutate,
  };
}

/** 受信中のフレンドリクエスト一覧を取得するSWRフック（30秒ごとに自動更新） */
export function useFriendRequests() {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading, mutate } = useSWR<Friend[]>(
    authKey(`${API_BASE_URL}/api/friends/requests`, isLoaded, isSignedIn),
    authFetcher,
    { refreshInterval: 30000 }
  );

  return {
    requests: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
    mutate,
  };
}

/** 指定ユーザーにフレンドリクエストを送信する */
export async function sendFriendRequest(friendUserId: string): Promise<Friend> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/friends/request`, {
    method: "POST",
    headers,
    body: JSON.stringify({ friend_user_id: friendUserId }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to send friend request: ${res.status}`);
  }

  return res.json();
}

/** 受信したフレンドリクエストを承認する */
export async function acceptFriendRequest(friendUserId: string): Promise<Friend> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/friends/accept`, {
    method: "POST",
    headers,
    body: JSON.stringify({ friend_user_id: friendUserId }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to accept friend request: ${res.status}`);
  }

  return res.json();
}

/** 受信したフレンドリクエストを拒否する */
export async function rejectFriendRequest(friendUserId: string): Promise<void> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/friends/reject`, {
    method: "POST",
    headers,
    body: JSON.stringify({ friend_user_id: friendUserId }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to reject friend request: ${res.status}`);
  }
}

/** フレンド関係を解除する */
export async function removeFriend(friendUserId: string): Promise<void> {
  const token = await getAuthToken();
  const headers: HeadersInit = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/friends/${friendUserId}`, {
    method: "DELETE",
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to remove friend: ${res.status}`);
  }
}
