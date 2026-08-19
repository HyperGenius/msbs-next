import useSWR, { mutate as globalMutate } from "swr";
import { useAuth } from "@clerk/nextjs";
import { Mission, BattleResult, BattleLog } from "@/types/battle";
import { API_BASE_URL, getAuthToken, fetcher, useAuthFetcher, authKey } from "./auth";

/**
 * 逐次パース結果をUIへ反映する間隔（行数）。
 * 1行ごとにコールバックすると大規模バトル（ログ10万件超）でSWRの再レンダーが
 * 高頻度に走りすぎるため、ある程度まとめて（バッチで）反映する（Issue #494）。
 */
const PROGRESSIVE_UPDATE_BATCH_SIZE = 500;

/** ミッション一覧を取得するSWRフック（認証不要・パブリック） */
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

/** 未読のバトル結果一覧を取得するSWRフック */
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

/** 指定バトルを既読状態にする */
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

/** バトル履歴を取得するSWRフック。limit件数分だけ取得する（デフォルト50件） */
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

/** 特定バトルの詳細を取得するSWRフック。battleIdがnullの場合はフェッチしない */
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
 * NDJSON（1行1エントリのJSON）レスポンスを1行ずつパースしてBattleLog配列にする。
 * バックエンドは大規模バトル（ログ10万件超）でもレスポンス全体を1個のJSON文字列に
 * 組み立てずチャンク送出するため（Issue #488）、フロント側も`res.json()`で全量の
 * 生テキストをまとめて保持せず、ReadableStreamから読めた分から逐次パースする。
 *
 * `onProgress` を渡すと、`PROGRESSIVE_UPDATE_BATCH_SIZE` 行パースするたびに
 * その時点までの配列（コピー）を通知する。全件パース完了を待たずに呼び出し元
 * （UI）へ段階的に反映するための仕組み（Issue #494）。
 */
export async function fetchBattleLogsNdjson(
  url: string,
  onProgress?: (logs: BattleLog[]) => void
): Promise<BattleLog[]> {
  const res = await fetch(url);
  if (!res.ok) {
    const error = new Error(`Failed to fetch data from ${url}: ${res.status} ${res.statusText}`) as Error & { status: number };
    error.status = res.status;
    throw error;
  }

  const logs: BattleLog[] = [];
  let sinceLastProgress = 0;

  const pushLog = (line: string) => {
    logs.push(JSON.parse(line));
    sinceLastProgress++;
    if (onProgress && sinceLastProgress >= PROGRESSIVE_UPDATE_BATCH_SIZE) {
      sinceLastProgress = 0;
      onProgress([...logs]);
    }
  };

  // ReadableStreamが使えない環境（一部のテスト用Response実装等）向けのフォールバック
  if (!res.body) {
    const text = await res.text();
    for (const line of text.split("\n")) {
      if (line.trim().length > 0) {
        pushLog(line);
      }
    }
    return logs;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    let newlineIndex = buffer.indexOf("\n");
    while (newlineIndex !== -1) {
      const line = buffer.slice(0, newlineIndex);
      buffer = buffer.slice(newlineIndex + 1);
      if (line.trim().length > 0) {
        pushLog(line);
      }
      newlineIndex = buffer.indexOf("\n");
    }
  }

  // ループ終了後にdecode()を引数なしで呼びデコーダーを終端する。
  // 通常のチャンク分割ではTextDecoderが未完成のマルチバイト列を内部で
  // 正しく繰り越して復元するため実害は出ないが、ストリームが本当に
  // マルチバイト文字の途中で打ち切られた場合（接続断など）にその分を
  // 静かに読み捨てず、置換文字として表面化させるための終端処理
  buffer += decoder.decode();

  // 末尾に改行なしで残った分（通常は末尾も改行区切りだが念のため）
  if (buffer.trim().length > 0) {
    pushLog(buffer);
  }

  return logs;
}

/**
 * バトルリプレイ用ログを取得するSWRフック。battleResultIdがnullの場合はフェッチしない。
 *
 * `fetchBattleLogsNdjson` の `onProgress` からSWRのグローバルキャッシュを直接
 * `mutate`することで、全件パース完了（Promise解決）を待たずに`logs`を段階的に
 * 更新する（Issue #494）。`isLoading`（`isValidating && !data`相当）は最初の
 * バッチが届いた時点でfalseになるため、呼び出し側は「初回データが届いたか」を
 * `isLoading`、「まだバックグラウンドで読み込み中か」を`isStreaming`で判別できる。
 */
export function useBattleLogs(battleResultId: string | null) {
  const key = battleResultId ? `${API_BASE_URL}/api/battles/${battleResultId}/logs` : null;

  const { data, error, isLoading, isValidating } = useSWR<BattleLog[]>(
    key,
    (fetchUrl: string) =>
      fetchBattleLogsNdjson(fetchUrl, (partialLogs) => {
        globalMutate(fetchUrl, partialLogs, { revalidate: false });
      })
  );

  return {
    logs: data,
    isLoading,
    isStreaming: isValidating,
    isError: error,
  };
}
