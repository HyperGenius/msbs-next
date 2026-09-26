"use client";

import useSWR from "swr";
import { DropTableDetail, DropTableUpdate } from "@/types/admin";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "";

const ENDPOINT = `${API_BASE_URL}/api/admin/drop-tables/batch`;

function adminFetcher(url: string) {
  return fetch(url, {
    headers: { "X-API-Key": ADMIN_API_KEY },
  }).then(async (res) => {
    if (!res.ok) {
      const err = new Error(`Failed to fetch ${url}: ${res.status} ${res.statusText}`) as Error & { status: number };
      err.status = res.status;
      throw err;
    }
    return res.json();
  });
}

/** FastAPI の 422 は detail が文字列（サービスの検証）か、項目ごとのエラーの配列（スキーマの検証）になる。 */
function errorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).join(".")}: ${d.msg ?? ""}`)
      .join(" / ");
  }
  return fallback;
}

/**
 * 定期バトルのドロップテーブルを取得・保存する SWR フック
 */
export function useAdminDropTable() {
  const { data, error, isLoading, mutate } = useSWR<DropTableDetail>(ENDPOINT, adminFetcher);

  async function saveDropTable(payload: DropTableUpdate): Promise<DropTableDetail> {
    const res = await fetch(ENDPOINT, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": ADMIN_API_KEY,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(errorMessage(body.detail, `Save failed: ${res.status}`));
    }
    const saved: DropTableDetail = await res.json();
    await mutate(saved, { revalidate: false });
    return saved;
  }

  return {
    dropTable: data,
    isLoading,
    isError: error,
    saveDropTable,
  };
}
