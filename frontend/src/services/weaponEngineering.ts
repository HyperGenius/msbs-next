import { WeaponUpgradeRequest, WeaponUpgradeResponse, WeaponUpgradePreview, WeaponUpgradeStatType } from "@/types/shop";
import { API_BASE_URL, getAuthToken } from "./auth";

/** 所持武器の custom_stats（power_bonus / accuracy_bonus）を1段階改造する */
export async function upgradePlayerWeapon(playerWeaponId: string, request: WeaponUpgradeRequest): Promise<WeaponUpgradeResponse> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/player-weapons/${playerWeaponId}/upgrade`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to upgrade weapon: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/** 武器改造前に費用と改造後の値をプレビュー取得する（確認ダイアログ表示に使用） */
export async function getWeaponUpgradePreview(playerWeaponId: string, statType: WeaponUpgradeStatType): Promise<WeaponUpgradePreview> {
  const token = await getAuthToken();
  const headers: HeadersInit = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/player-weapons/${playerWeaponId}/upgrade-preview/${statType}`, {
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to get weapon upgrade preview: ${res.status} ${res.statusText}`);
  }

  return res.json();
}
