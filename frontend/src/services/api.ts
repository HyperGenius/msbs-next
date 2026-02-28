/* frontend/src/services/api.ts */
import useSWR from "swr";
import { Mission, BattleResult, MobileSuit, MobileSuitUpdate, EntryStatusResponse, BattleEntry, Pilot, ShopListing, PurchaseResponse, UpgradeRequest, UpgradeResponse, UpgradePreview, BulkUpgradeRequest, BulkUpgradeResponse, SkillDefinition, SkillUnlockRequest, SkillUnlockResponse, WeaponListing, WeaponPurchaseResponse, EquipWeaponRequest, LeaderboardEntry, PlayerProfile, Friend, Team, TeamEntryRequest, TeamEntryResponse } from "@/types/battle";

// Backend API Base URL
// 本番環境では環境変数NEXT_PUBLIC_API_URLを使用
// ローカル開発では localhost:8000 にフォールバック
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

/**
 * Get auth token from Clerk (client-side only)
 *
 * Note: This uses window.Clerk which is available after ClerkProvider loads.
 * For better type safety, consider using useAuth() hook in components
 * and passing the token explicitly to API functions.
 */
async function getAuthToken(): Promise<string | null> {
  if (typeof window !== 'undefined') {
    // Client-side: get token from window.Clerk
    // TypeScript note: Clerk types are not directly exposed on window
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
  const { data, error, isLoading, mutate } = useSWR<BattleResult[]>(
    `${API_BASE_URL}/api/battles/unread`,
    fetcher
  );

  return {
    unreadBattles: data,
    isLoading,
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
  const { data, error, isLoading, mutate } = useSWR<BattleResult[]>(
    `${API_BASE_URL}/api/battles?limit=${limit}`,
    fetcher
  );

  return {
    battles: data,
    isLoading,
    isError: error,
    mutate,
  };
}

/**
 * 特定のバトル詳細を取得するSWRフック
 */
export function useBattleDetail(battleId: string | null) {
  const { data, error, isLoading } = useSWR<BattleResult>(
    battleId ? `${API_BASE_URL}/api/battles/${battleId}` : null,
    fetcher
  );

  return {
    battle: data,
    isLoading,
    isError: error,
  };
}

/**
 * エントリー状況を取得するSWRフック
 */
export function useEntryStatus() {
  const { data, error, isLoading, mutate } = useSWR<EntryStatusResponse>(
    `${API_BASE_URL}/api/entries/status`,
    fetcher
  );

  return {
    entryStatus: data,
    isLoading,
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
 */
export function usePilot() {
  const { data, error, isLoading, mutate } = useSWR<Pilot>(
    `${API_BASE_URL}/api/pilots/me`,
    fetcher
  );

  return {
    pilot: data,
    isLoading,
    isError: error,
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
 * ショップ商品一覧を取得するSWRフック
 */
export function useShopListings() {
  const { data, error, isLoading } = useSWR<ShopListing[]>(
    `${API_BASE_URL}/api/shop/listings`,
    fetcher
  );

  return {
    listings: data,
    isLoading,
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
  
  return {
    profile: data,
    isLoading,
    isError: error,
  };
}

// ===== フレンド機能 =====

/**
 * フレンド一覧を取得するSWRフック
 */
export function useFriends() {
  const { data, error, isLoading, mutate } = useSWR<Friend[]>(
    `${API_BASE_URL}/api/friends/`,
    fetcher
  );

  return {
    friends: data,
    isLoading,
    isError: error,
    mutate,
  };
}

/**
 * 受信中のフレンドリクエスト一覧を取得するSWRフック
 */
export function useFriendRequests() {
  const { data, error, isLoading, mutate } = useSWR<Friend[]>(
    `${API_BASE_URL}/api/friends/requests`,
    fetcher,
    { refreshInterval: 30000 }
  );

  return {
    requests: data,
    isLoading,
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
  const { data, error, isLoading, mutate } = useSWR<Team | null>(
    `${API_BASE_URL}/api/teams/current`,
    fetcher,
    { refreshInterval: 5000 }
  );

  return {
    team: data,
    isLoading,
    isError: error,
    mutate,
  };
}

/**
 * チームステータスをリアルタイムに近い間隔でポーリングするSWRフック
 * メンバーの参加・Ready状態を画面に反映させる
 */
export function useTeamStatus() {
  const { data, error, isLoading, mutate } = useSWR<Team | null>(
    `${API_BASE_URL}/api/teams/current`,
    fetcher,
    { refreshInterval: 5000 }
  );

  return {
    team: data,
    isLoading,
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

