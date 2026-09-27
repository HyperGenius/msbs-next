"use client";

import useSWR from "swr";
import { MasterTechnology, MasterTechnologyUpdate } from "@/types/admin";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "";

const ENDPOINT = `${API_BASE_URL}/api/admin/technologies`;

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

async function request<T>(url: string, method: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": ADMIN_API_KEY,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(errorMessage(detail.detail, `${method} failed: ${res.status}`));
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

/**
 * 技術マスターを取得・変更する SWR フック。
 * 保存後は backend の返した値でキャッシュを置き換える（技術ID順に並べ直す）。
 */
export function useAdminTechnologies() {
  const { data, error, isLoading, mutate } = useSWR<MasterTechnology[]>(ENDPOINT, adminFetcher);

  const sortById = (list: MasterTechnology[]) =>
    [...list].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));

  async function createTechnology(payload: MasterTechnology): Promise<MasterTechnology> {
    const created = await request<MasterTechnology>(ENDPOINT, "POST", payload);
    await mutate(sortById([...(data ?? []), created]), { revalidate: false });
    return created;
  }

  async function updateTechnology(
    techId: string,
    payload: MasterTechnologyUpdate
  ): Promise<MasterTechnology> {
    const updated = await request<MasterTechnology>(`${ENDPOINT}/${techId}`, "PUT", payload);
    await mutate(
      (data ?? []).map((t) => (t.id === techId ? updated : t)),
      { revalidate: false }
    );
    return updated;
  }

  async function deleteTechnology(techId: string): Promise<void> {
    await request<void>(`${ENDPOINT}/${techId}`, "DELETE");
    await mutate(
      (data ?? []).filter((t) => t.id !== techId),
      { revalidate: false }
    );
  }

  return {
    technologies: data,
    isLoading,
    isError: error,
    createTechnology,
    updateTechnology,
    deleteTechnology,
  };
}
