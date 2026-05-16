import { UpgradeRequest, UpgradeResponse, UpgradePreview, BulkUpgradeRequest, BulkUpgradeResponse } from "@/types/battle";
import { API_BASE_URL, getAuthToken } from "./auth";

/** 指定ステータスを1段階強化する */
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

/** 複数ステータスを一括で強化する（個別強化のN回分をまとめてAPIコールを1回にする） */
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

/** 強化前に費用と強化後の値をプレビュー取得する（確認ダイアログ表示に使用） */
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
