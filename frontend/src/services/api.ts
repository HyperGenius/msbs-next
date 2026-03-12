/* frontend/src/services/api.ts */
import useSWR from "swr";
import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";
import { Mission, BattleResult, MobileSuit, MobileSuitUpdate, EntryStatusResponse, BattleEntry, Pilot, ShopListing, PurchaseResponse, UpgradeRequest, UpgradeResponse, UpgradePreview, BulkUpgradeRequest, BulkUpgradeResponse, SkillDefinition, SkillUnlockRequest, SkillUnlockResponse, WeaponListing, WeaponPurchaseResponse, EquipWeaponRequest, LeaderboardEntry, PlayerProfile, Friend, Team, TeamEntryRequest, TeamEntryResponse } from "@/types/battle";
import { EnrichedMobileSuit, enrichMobileSuit } from "@/utils/rankUtils";

/** PlayerProfile の mobile_suit フィールドが EnrichedMobileSuit に変換された型 */
export type EnrichedPlayerProfile = Omit<PlayerProfile, "mobile_suit"> & {
  mobile_suit: EnrichedMobileSuit | null;
};

// Backend API Base URL
// 本番環境では環境変数NEXT_PUBLIC_API_URLを使用
// ローカル開発では localhost:8000 にフォールバック
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

/**
 * Get auth token from Clerk (client-side only)
 *
 * Used by imperative (non-hook) API functions called from event handlers,
 * where Clerk is guaranteed to be initialized before the user can interact.
 */
async function getAuthToken(): Promise<string | null> {
  if (typeof window !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const clerk = (window as any).Clerk;
    if (clerk && clerk.session) {
      return await clerk.session.getToken();
    }
  }
  return null;
}

/**
 * SWR用のfetcher関数（認証不要なパブリックエンドポイント向け）
 */
const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) {
    const error = new Error(`Failed to fetch data from ${url}: ${res.status} ${res.statusText}`) as Error & { status: number };
    error.status = res.status;
    throw error;
  }
  return res.json();
};

/**
 * 認証済みSWRフェッチャーを返すフック
 *
 * `useAuth` の `getToken` を利用してトークンを取得するため、
 * Clerk の初期化完了後に正しく Bearer トークンをリクエストヘッダーに付与します。
 *
 * @returns `(url: string) => Promise<any>` — SWR の fetcher として利用可能な非同期関数
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function useAuthFetcher(): (url: string) => Promise<any> {
  const { getToken } = useAuth();
  return useCallback(async (url: string) => {
    const token = await getToken();
    const headers: HeadersInit = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(url, { headers });
    if (!res.ok) {
      const error = new Error(`Failed to fetch data from ${url}: ${res.status} ${res.statusText}`) as Error & { status: number };
      error.status = res.status;
      throw error;
    }
    return res.json();
  }, [getToken]);
}

/**
 * 認証状態に基づいてSWRのキーを返すヘルパー
 *
 * Clerk の初期化（`isLoaded`）とサインイン状態（`isSignedIn`）を確認し、
 * 両方が `true` の場合のみ URL を返します。それ以外は `null` を返すことで、
 * 認証完了前に SWR がリクエストを送出するのを防ぎます。
 *
 * @param url - フェッチ対象のURL
 * @param isLoaded - Clerk の初期化が完了しているか
 * @param isSignedIn - ユーザーがサインイン済みか
 * @returns URL または null
 */
function authKey(url: string, isLoaded: boolean, isSignedIn: boolean | null | undefined): string | null {
  return isLoaded && isSignedIn ? url : null;
}

/**
 * 機体一覧を取得するSWRフック
 */
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

/**
 * ミッション一覧を取得するSWRフック
 */
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

/**
 * 未読バトル結果を取得するSWRフック
 */
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

/**
 * バトル結果を既読にする関数
 */
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

/**
 * バトル履歴を取得するSWRフック
 */
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

/**
 * 特定のバトル詳細を取得するSWRフック
 */
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

/**
 * エントリー状況を取得するSWRフック
 */
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

/**
 * エントリー数を取得するSWRフック
 */
export function useEntryCount() {
  const { data, error, isLoading, mutate } = useSWR<{ count: number }>(
    `${API_BASE_URL}/api/entries/count`,
    fetcher,
    { refreshInterval: 10000 } // 10秒ごとに自動更新
  );

  return {
    entryCount: data?.count ?? 0,
    isLoading,
    isError: error,
    mutate,
  };
}

/**
 * エントリーを作成する関数
 */
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

/**
 * エントリーをキャンセルする関数
 */
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

/**
 * パイロット情報を取得するSWRフック
 * 404エラーの場合はisNotFoundフラグを返す
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

/**
 * 新規パイロットを作成する関数
 */
export async function createPilot(
  name: string,
  starterUnitId: "zaku_ii" | "gm"
): Promise<Pilot> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(`${API_BASE_URL}/api/pilots/create`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      name,
      starter_unit_id: starterUnitId,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to create pilot: ${res.status} ${res.statusText}`
    );
  }

  return res.json();
}

/**
 * パイロットを登録する関数（オンボーディング用）
 */
export async function registerPilot(
  name: string,
  faction: "FEDERATION" | "ZEON"
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
    body: JSON.stringify({ name, faction }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to register pilot: ${res.status} ${res.statusText}`
    );
  }

  return res.json();
}

/**
 * ショップ商品一覧を取得するSWRフック
 */
export function useShopListings() {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading } = useSWR<ShopListing[]>(
    authKey(`${API_BASE_URL}/api/shop/listings`, isLoaded, isSignedIn),
    authFetcher
  );

  return {
    listings: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
  };
}

/**
 * モビルスーツを購入する関数
 */
export async function purchaseMobileSuit(itemId: string): Promise<PurchaseResponse> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(`${API_BASE_URL}/api/shop/purchase/${itemId}`, {
    method: "POST",
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to purchase: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * 武器ショップ商品一覧を取得するSWRフック
 */
export function useWeaponListings() {
  const { data, error, isLoading } = useSWR<WeaponListing[]>(
    `${API_BASE_URL}/api/shop/weapons`,
    fetcher
  );

  return {
    weaponListings: data,
    isLoading,
    isError: error,
  };
}

/**
 * 武器を購入する関数
 */
export async function purchaseWeapon(weaponId: string): Promise<WeaponPurchaseResponse> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(`${API_BASE_URL}/api/shop/purchase/weapon/${weaponId}`, {
    method: "POST",
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to purchase weapon: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * 機体に武器を装備する関数
 */
export async function equipWeapon(mobileSuitId: string, request: EquipWeaponRequest): Promise<MobileSuit> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(`${API_BASE_URL}/api/mobile_suits/${mobileSuitId}/equip`, {
    method: "PUT",
    headers,
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to equip weapon: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * 機体を強化する関数
 */
export async function upgradeMobileSuit(request: UpgradeRequest): Promise<UpgradeResponse> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(`${API_BASE_URL}/api/engineering/upgrade`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to upgrade: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * 機体の複数ステータスを一括強化する関数
 */
export async function bulkUpgradeMobileSuit(request: BulkUpgradeRequest): Promise<BulkUpgradeResponse> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/engineering/bulk-upgrade`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to bulk upgrade: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * 強化プレビューを取得する関数
 */
export async function getUpgradePreview(mobileSuitId: string, statType: string): Promise<UpgradePreview> {
  const token = await getAuthToken();
  const headers: HeadersInit = {};
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const res = await fetch(`${API_BASE_URL}/api/engineering/preview/${mobileSuitId}/${statType}`, {
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to get preview: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * 利用可能なスキル一覧を取得するSWRフック
 */
export function useSkills() {
  const { data, error, isLoading } = useSWR<SkillDefinition[]>(
    `${API_BASE_URL}/api/pilots/skills`,
    fetcher
  );

  return {
    skills: data,
    isLoading,
    isError: error,
  };
}

/**
 * スキルを習得または強化する関数
 */
export async function unlockSkill(skillId: string): Promise<SkillUnlockResponse> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const request: SkillUnlockRequest = { skill_id: skillId };
  
  const res = await fetch(`${API_BASE_URL}/api/pilots/skills/unlock`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to unlock skill: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * ステータスポイントを割り振るリクエスト型
 */
export interface StatusAllocateRequest {
  dex?: number;
  intel?: number;
  ref?: number;
  tou?: number;
  luk?: number;
}

/**
 * ステータスポイントを各ステータスへ割り振る関数
 */
export async function allocateStatusPoints(request: StatusAllocateRequest): Promise<Pilot> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const body = {
    dex: request.dex ?? 0,
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

/**
 * パイロット名を更新する関数
 */
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
 * 現在のランキングを取得するSWRフック
 */
export function useRankings(limit: number = 100) {
  const { data, error, isLoading, mutate } = useSWR<LeaderboardEntry[]>(
    `${API_BASE_URL}/api/rankings/current?limit=${limit}`,
    fetcher
  );
  
  return {
    rankings: data,
    isLoading,
    isError: error,
    mutate,
  };
}

/**
 * プレイヤープロフィールを取得するSWRフック
 */
export function usePlayerProfile(userId: string | null) {
  const { data, error, isLoading } = useSWR<PlayerProfile>(
    userId ? `${API_BASE_URL}/api/rankings/pilot/${userId}/profile` : null,
    fetcher
  );

  const profile: EnrichedPlayerProfile | undefined = data
    ? {
        ...data,
        mobile_suit: data.mobile_suit ? enrichMobileSuit(data.mobile_suit) : null,
      }
    : undefined;

  return {
    profile,
    isLoading,
    isError: error,
  };
}

// ===== フレンド機能 =====

/**
 * フレンド一覧を取得するSWRフック
 */
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

/**
 * 受信中のフレンドリクエスト一覧を取得するSWRフック
 */
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

/**
 * フレンドリクエストを送信する関数
 */
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

/**
 * フレンドリクエストを承認する関数
 */
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

/**
 * フレンドリクエストを拒否する関数
 */
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

/**
 * フレンドを解除する関数
 */
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

// ===== チーム機能 =====

/**
 * 現在のチーム情報を取得するSWRフック
 */
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
 * チームステータスをリアルタイムに近い間隔でポーリングするSWRフック
 * メンバーの参加・Ready状態を画面に反映させる
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

/**
 * チームを作成する関数
 */
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

/**
 * チームにメンバーを招待する関数
 */
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

/**
 * Ready状態をトグルする関数
 */
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

/**
 * チームから離脱する関数
 */
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

/**
 * アカウントをリセットする関数（デバッグ用）
 * 現在のユーザーに紐づく全データ（パイロット、機体、戦績）を削除する
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

/**
 * チーム単位でバトルにエントリーする関数
 */
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

