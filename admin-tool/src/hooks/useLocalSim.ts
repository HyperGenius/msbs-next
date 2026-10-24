"use client";

import useSWR from "swr";
import type {
  LocalSimGenerationDetail,
  LocalSimManifest,
  LocalSimRosterInfo,
  LocalSimRun,
  LocalSimRunRequest,
} from "@/types/localSim";

const BASE = "/api/local-sim";
const POLL_INTERVAL_MS = 1000;

async function localFetcher<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status} ${res.statusText}`);
  return res.json();
}

async function localRequest<T>(url: string, method: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : `${method} ${url}: ${res.status}`);
  return data as T;
}

/** ロスターの一覧 */
export function useLocalSimRosters() {
  const { data, error, isLoading } = useSWR<{ root: string; rosters: LocalSimRosterInfo[] }>(
    `${BASE}/rosters`,
    localFetcher
  );
  return { root: data?.root, rosters: data?.rosters ?? [], error, isLoading };
}

/** 世代の一覧（新しい順）と、ピン留めの切り替え */
export function useLocalSimGenerations() {
  const { data, error, isLoading, mutate } = useSWR<{ root: string; generations: LocalSimManifest[] }>(
    `${BASE}/generations`,
    localFetcher
  );

  async function setPinned(generationId: string, pinned: boolean) {
    await localRequest(`${BASE}/generations/${encodeURIComponent(generationId)}`, "PATCH", { pinned });
    await mutate();
  }

  return { generations: data?.generations ?? [], error, isLoading, refresh: mutate, setPinned };
}

/** 世代の詳細（manifest と report） */
export function useLocalSimGeneration(generationId: string | null) {
  const { data, error, isLoading } = useSWR<LocalSimGenerationDetail>(
    generationId ? `${BASE}/generations/${encodeURIComponent(generationId)}` : null,
    localFetcher
  );
  return { detail: data, error, isLoading };
}

/**
 * 実行の開始・中止と、進捗のポーリング。
 * 実行中だけ 1 秒ごとに取り直す。
 */
export function useLocalSimRun() {
  const { data, mutate } = useSWR<{ run: LocalSimRun | null }>(`${BASE}/runs/current`, localFetcher, {
    refreshInterval: (latest) => (latest?.run?.status === "running" ? POLL_INTERVAL_MS : 0),
  });
  const run = data?.run ?? null;

  async function start(request: LocalSimRunRequest) {
    const started = await localRequest<LocalSimRun>(`${BASE}/runs`, "POST", request);
    await mutate({ run: started }, { revalidate: false });
  }

  async function cancel() {
    const result = await localRequest<{ run: LocalSimRun | null }>(`${BASE}/runs/current`, "DELETE");
    await mutate(result, { revalidate: false });
  }

  return { run, isRunning: run?.status === "running", start, cancel };
}
