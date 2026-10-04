"use client";

import useSWR from "swr";
import { DropTableDetail, DropTableScopeSummary, DropTableUpdate } from "@/types/admin";
import { adminFetcher, adminRequest, adminUrl } from "@/lib/adminApi";

type DropTableScope = Pick<DropTableScopeSummary, "scope_type" | "scope_key">;

const LIST_ENDPOINT = adminUrl("/drop-tables");

function endpointFor(scope: DropTableScope): string {
  if (scope.scope_type === "BATCH") return adminUrl("/drop-tables/batch");
  return adminUrl(`/drop-tables/theaters/${encodeURIComponent(scope.scope_key)}`);
}

/**
 * 共通テーブルと全戦域について、テーブルの有無を取得する SWR フック
 */
export function useAdminDropTableScopes() {
  const { data, error, isLoading, mutate } = useSWR<DropTableScopeSummary[]>(LIST_ENDPOINT, adminFetcher);
  return { scopes: data, isLoading, isError: error, reloadScopes: mutate };
}

/**
 * 共通テーブルか戦域のドロップテーブルを取得・保存・削除する SWR フック。
 * 戦域のテーブルを削除すると、その戦域は共通テーブルで抽選する。
 */
export function useAdminDropTable(scope: DropTableScope | null) {
  const endpoint = scope ? endpointFor(scope) : null;
  const { data, error, isLoading, mutate } = useSWR<DropTableDetail>(endpoint, adminFetcher);

  async function saveDropTable(payload: DropTableUpdate): Promise<DropTableDetail> {
    if (!endpoint) throw new Error("No drop table is selected");
    const saved = await adminRequest<DropTableDetail>(endpoint, "PUT", payload);
    await mutate(saved, { revalidate: false });
    return saved;
  }

  /** 戦域のテーブルを削除し、共通テーブルの内容を取り直す */
  async function deleteDropTable(): Promise<void> {
    if (!endpoint) throw new Error("No drop table is selected");
    await adminRequest<void>(endpoint, "DELETE");
    await mutate();
  }

  return {
    dropTable: data,
    isLoading,
    isError: error,
    saveDropTable,
    deleteDropTable,
  };
}
