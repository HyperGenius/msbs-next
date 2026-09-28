const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "";

/** 管理APIの URL を返す（例: adminUrl("/theaters")） */
export function adminUrl(path: string): string {
  return `${API_BASE_URL}/api/admin${path}`;
}

/** SWR 用の fetcher。管理APIキーを付けて GET する */
export function adminFetcher(url: string) {
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
export function errorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).join(".")}: ${d.msg ?? ""}`)
      .join(" / ");
  }
  return fallback;
}

/** 管理APIに変更系のリクエストを送る。失敗したら backend の detail を message にして投げる */
export async function adminRequest<T>(url: string, method: string, body?: unknown): Promise<T> {
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
