import useSWR from "swr";
import { useAuth } from "@clerk/nextjs";
import { MobileSuit, ShopListing, PurchaseResponse, WeaponListing, WeaponPurchaseResponse, EquipWeaponRequest } from "@/types/battle";
import { API_BASE_URL, getAuthToken, fetcher, useAuthFetcher, authKey } from "./auth";

/** ショップに陳列されている機体一覧を取得するSWRフック */
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

/** 指定IDの機体を購入する */
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

/** 武器ショップの商品一覧を取得するSWRフック（認証不要・パブリック） */
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

/** 指定IDの武器を購入する */
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

/** 指定機体のスロットに武器インスタンスを装備する */
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

/** 所有武器インスタンスを売却・破棄する */
export async function deletePlayerWeapon(playerWeaponId: string): Promise<void> {
  const token = await getAuthToken();
  const headers: HeadersInit = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/api/player-weapons/${playerWeaponId}`, {
    method: "DELETE",
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete player weapon: ${res.status} ${res.statusText}`);
  }
}
