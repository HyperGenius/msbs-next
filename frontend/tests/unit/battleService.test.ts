import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { markBattleAsRead, fetchBattleLogsNdjson } from "@/services/battle";

vi.mock("@/services/auth", async () => {
  const actual = await vi.importActual<typeof import("@/services/auth")>("@/services/auth");
  return { ...actual, getAuthToken: vi.fn().mockResolvedValue("test-token") };
});

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ─────────────────────────────────────────────
// markBattleAsRead — バトル結果を既読にする
// ─────────────────────────────────────────────
describe("markBattleAsRead", () => {
  it("成功時に何も返さない（void）", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    const result = await markBattleAsRead("battle-1");

    expect(result).toBeUndefined();
  });

  it("POSTメソッドとreadエンドポイントでfetchを呼び出す", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    await markBattleAsRead("battle-abc");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/battles/battle-abc/read"),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("Authorizationヘッダーにトークンを付与する", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as unknown as Response);

    await markBattleAsRead("battle-1");

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect((options as RequestInit).headers).toMatchObject({
      Authorization: "Bearer test-token",
    });
  });

  it("バトルが見つからない場合にdetailメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: () => Promise.resolve({ detail: "バトル結果が見つかりません" }),
    } as unknown as Response);

    await expect(markBattleAsRead("battle-1")).rejects.toThrow("バトル結果が見つかりません");
  });

  it("APIがdetailなしでエラーを返したときフォールバックメッセージで例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({}),
    } as unknown as Response);

    await expect(markBattleAsRead("battle-1")).rejects.toThrow("500");
  });
});

// ─────────────────────────────────────────────
// fetchBattleLogsNdjson — NDJSONレスポンスの逐次パース
// ─────────────────────────────────────────────

/** 文字列をチャンクに分割してReadableStreamのbodyを持つResponseを作る */
const mockNdjsonResponse = (text: string, chunkSize = 5): Response => {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(text);
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (let i = 0; i < bytes.length; i += chunkSize) {
        controller.enqueue(bytes.slice(i, i + chunkSize));
      }
      controller.close();
    },
  });
  return { ok: true, body: stream } as unknown as Response;
};

describe("fetchBattleLogsNdjson", () => {
  it("改行区切りのNDJSONを1行ずつパースしてBattleLog配列を返す", async () => {
    const ndjson =
      '{"timestamp":0,"actor_id":"a","action_type":"MOVE","message":"m1","position_snapshot":{"x":0,"y":0,"z":0}}\n' +
      '{"timestamp":1,"actor_id":"b","action_type":"ATTACK","message":"m2","position_snapshot":{"x":1,"y":0,"z":0}}\n';
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(ndjson));

    const logs = await fetchBattleLogsNdjson("http://example.com/logs");

    expect(logs).toHaveLength(2);
    expect(logs[0].action_type).toBe("MOVE");
    expect(logs[1].action_type).toBe("ATTACK");
  });

  it("チャンク境界が行の途中で切れても正しくパースできる", async () => {
    const ndjson = '{"timestamp":0,"actor_id":"a","action_type":"MOVE","message":"long message here","position_snapshot":{"x":0,"y":0,"z":0}}\n';
    // チャンクサイズ1バイトずつに分割し、意図的にJSONの途中でチャンクを跨がせる
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(ndjson, 1));

    const logs = await fetchBattleLogsNdjson("http://example.com/logs");

    expect(logs).toHaveLength(1);
    expect(logs[0].message).toBe("long message here");
  });

  it("末尾に改行が無い最終行も取りこぼさずパースする", async () => {
    const ndjson = '{"timestamp":0,"actor_id":"a","action_type":"WAIT","message":"no trailing newline","position_snapshot":{"x":0,"y":0,"z":0}}';
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(ndjson));

    const logs = await fetchBattleLogsNdjson("http://example.com/logs");

    expect(logs).toHaveLength(1);
    expect(logs[0].message).toBe("no trailing newline");
  });

  it("空のレスポンス（ログ無し）で空配列を返す", async () => {
    vi.mocked(fetch).mockResolvedValue(mockNdjsonResponse(""));

    const logs = await fetchBattleLogsNdjson("http://example.com/logs");

    expect(logs).toEqual([]);
  });

  it("res.bodyが無い環境ではres.text()にフォールバックしてパースする", async () => {
    const ndjson =
      '{"timestamp":0,"actor_id":"a","action_type":"MOVE","message":"m1","position_snapshot":{"x":0,"y":0,"z":0}}\n';
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      body: null,
      text: () => Promise.resolve(ndjson),
    } as unknown as Response);

    const logs = await fetchBattleLogsNdjson("http://example.com/logs");

    expect(logs).toHaveLength(1);
    expect(logs[0].action_type).toBe("MOVE");
  });

  it("エラーレスポンス時はstatusを含む例外を投げる", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
    } as unknown as Response);

    await expect(fetchBattleLogsNdjson("http://example.com/logs")).rejects.toThrow("404");
  });
});
